from decimal import ROUND_HALF_UP
from decimal import Decimal
from decimal import InvalidOperation
from typing import Any

import stripe
from django.db import models
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import FSMModelMixin
from django_fsm import transition
from djstripe.models import Refund as StripeRefund

from neuromancers_network.core.models.base import Timestamped
from neuromancers_network.meetings.models.request import MeetingRequest

from .choices import RefundStatus


def _to_minor_units(value) -> int:
    """Coerce a major-unit monetary *value* into integer minor units."""
    try:
        amount = Decimal(str(value))
    except InvalidOperation, ValueError:
        message = "Refund amount is not a valid number"
        raise ValueError(message) from None
    if amount <= 0:
        message = "Refund amount must be greater than zero"
        raise ValueError(message)
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class RefundRequest(FSMModelMixin, Timestamped):
    meeting_request = models.OneToOneField(
        MeetingRequest,
        on_delete=models.CASCADE,
        related_name="refund_request",
    )
    reason = models.TextField(_("Reason"))
    status = FSMField(
        _("Status"),
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
    )
    stripe_refund_id = models.CharField(
        _("Stripe refund ID"),
        max_length=255,
        blank=True,
    )
    peer_response = models.TextField(_("Peer response"), blank=True)

    @property
    def needs_approval(self) -> bool:
        return self.meeting_request.meeting.refund_requires_approval

    def request_refund(self, amount=None):
        """Create or process the Stripe refund based on the meeting policy.

        Serialised with ``select_for_update`` so two requests cannot both pass the
        pending check; the Stripe call also carries an idempotency key as a second
        line of defence.
        """
        with transaction.atomic():
            locked = type(self).objects.select_for_update().get(pk=self.pk)
            if locked.status == RefundStatus.REJECTED:
                locked.reopen()
                locked.save(
                    update_fields=["status", "peer_response", "updated_at"],
                )
            if locked.status != RefundStatus.PENDING:
                self.refresh_from_db()
                return self

            if locked.needs_approval:
                locked.save(update_fields=["updated_at"])
                self.refresh_from_db()
                return self

            refund = locked.issue_stripe_refund(amount=amount)
            locked.stripe_refund_id = refund.id
            locked.mark_refunded()
            locked.save(update_fields=["stripe_refund_id", "status", "updated_at"])
            self.refresh_from_db()
        return self

    @transition(
        field=status,
        source=RefundStatus.PENDING,
        target=RefundStatus.APPROVED,
    )
    def approve(self, amount=None):
        refund = self.issue_stripe_refund(amount=amount)
        self.stripe_refund_id = refund.id

    @transition(
        field=status,
        source=RefundStatus.PENDING,
        target=RefundStatus.REJECTED,
    )
    def reject(self):
        pass

    @transition(
        field=status,
        source=RefundStatus.REJECTED,
        target=RefundStatus.PENDING,
    )
    def reopen(self):
        """Allow a rejected refund to be raised again."""
        self.peer_response = ""

    @transition(
        field=status,
        source=[RefundStatus.PENDING, RefundStatus.APPROVED],
        target=RefundStatus.REFUNDED,
    )
    def mark_refunded(self):
        pass

    def issue_stripe_refund(self, amount=None):
        """Issue a refund against the meeting request's payment intent.

        Pass *amount* (major units) for a partial refund, permitted only when
        partial refunds are enabled. Full refunds are always allowed. The refund
        is issued against the peer's connected account per the charge type.
        """
        from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415
        from neuromancers_network.payments.charges import (  # noqa: PLC0415
            build_refund_kwargs,
        )

        stripe_settings = StripeSettings.load()
        if not stripe_settings.secret_key:
            error_message = "Stripe secret key is not configured"
            raise ValueError(error_message)

        payment_intent_id = self.meeting_request.stripe_payment_intent_id
        if not payment_intent_id:
            error_message = "Meeting request has no payment intent to refund"
            raise ValueError(error_message)

        refund_kwargs: dict[str, Any] = {"payment_intent": payment_intent_id}
        idempotency_key = f"refund:{self.meeting_request_id}"
        if amount is not None:
            if not stripe_settings.allow_partial_refunds:
                error_message = "Partial refunds are not enabled"
                raise ValueError(error_message)
            amount_minor = _to_minor_units(amount)
            paid = self.meeting_request.price_paid
            if paid is None or paid <= 0:
                error_message = "Meeting request has no recorded payment to refund"
                raise ValueError(error_message)
            if amount_minor > _to_minor_units(paid):
                error_message = "Refund amount exceeds the amount paid"
                raise ValueError(error_message)
            refund_kwargs["amount"] = amount_minor
            idempotency_key = f"{idempotency_key}:{amount_minor}"

        peer_profile = getattr(
            self.meeting_request.meeting.peer,
            "payment_profile",
            None,
        )
        destination = (
            peer_profile.stripe_connect_account_id_id
            if peer_profile is not None
            else None
        )
        refund_kwargs.update(
            build_refund_kwargs(
                stripe_settings=stripe_settings,
                destination=destination,
            ),
        )

        stripe.api_key = stripe_settings.secret_key
        refund_kwargs["idempotency_key"] = idempotency_key
        refund = stripe.Refund.create(**refund_kwargs)
        StripeRefund.sync_from_stripe_data(refund, api_key=stripe_settings.secret_key)
        return refund
