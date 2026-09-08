import stripe
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import transition
from djstripe.models import Refund as StripeRefund

from neuromancers_network.core.models.base import Timestamped
from neuromancers_network.meetings.models.request import MeetingRequest

from .choices import RefundStatus


class RefundRequest(Timestamped):
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

    def request_refund(self):
        """Create or process the Stripe refund based on the meeting policy."""
        if self.status != RefundStatus.PENDING:
            return self

        if self.needs_approval:
            self.save(update_fields=["updated_at"])
            return self

        refund = self.issue_stripe_refund()
        self.stripe_refund_id = refund.id
        self.mark_refunded()
        self.save(update_fields=["stripe_refund_id", "status", "updated_at"])
        return self

    @transition(
        field=status,
        source=RefundStatus.PENDING,
        target=RefundStatus.APPROVED,
    )
    def approve(self):
        refund = self.issue_stripe_refund()
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
        source=[RefundStatus.PENDING, RefundStatus.APPROVED],
        target=RefundStatus.REFUNDED,
    )
    def mark_refunded(self):
        pass

    def issue_stripe_refund(self):
        """Issue a full refund against the meeting request's payment intent."""
        from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415

        stripe_settings = StripeSettings.load()
        if not stripe_settings.secret_key:
            error_message = "Stripe secret key is not configured"
            raise ValueError(error_message)

        payment_intent_id = self.meeting_request.stripe_payment_intent_id
        if not payment_intent_id:
            error_message = "Meeting request has no payment intent to refund"
            raise ValueError(error_message)

        stripe.api_key = stripe_settings.secret_key
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
        )
        StripeRefund.sync_from_stripe_data(refund, api_key=stripe_settings.secret_key)
        return refund
