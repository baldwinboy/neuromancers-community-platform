from datetime import timedelta
from decimal import Decimal

import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import GET_STATE
from django_fsm import FSMField
from django_fsm import FSMModelMixin
from django_fsm import can_proceed
from django_fsm import transition
from djstripe.models import Session as StripeSession

from neuromancers_network.core.models.base import Timestamped

from .choices import MeetingRequestStatus
from .choices import MeetingType
from .meeting import MAX_DURATION_MINUTES
from .meeting import MIN_DURATION_MINUTES
from .meeting import Meeting


def _approval_target(request, *_args, **_kwargs):
    if request.meeting.requires_payment_before_join:
        return MeetingRequestStatus.PENDING_PAYMENT
    return MeetingRequestStatus.APPROVED


class MeetingRequest(FSMModelMixin, Timestamped):
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    support_seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meeting_requests",
    )
    status = FSMField(
        _("Status"),
        default=MeetingRequestStatus.PENDING_APPROVAL,
        choices=MeetingRequestStatus.choices,
    )
    price_paid = models.DecimalField(
        _("Price paid"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    seeker_terms = models.TextField(
        _("Support seeker terms / needs"),
        blank=True,
    )
    peer_terms = models.TextField(
        _("Peer terms of engagement"),
        blank=True,
    )
    stripe_payment_intent_id = models.CharField(
        _("Stripe payment intent ID"),
        max_length=255,
        blank=True,
    )
    stripe_checkout_session_id = models.CharField(
        _("Stripe checkout session ID"),
        max_length=255,
        blank=True,
    )
    receipt_url = models.URLField(
        _("Receipt URL"),
        max_length=500,
        blank=True,
    )
    booking = models.ForeignKey(
        "meetings.Booking",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sessions",
    )
    access_needs = models.TextField(_("Access needs"), blank=True)
    terms_accepted = models.BooleanField(_("Terms accepted"), default=False)
    terms_accepted_at = models.DateTimeField(
        _("Terms accepted at"),
        null=True,
        blank=True,
    )

    # Seeker-requested scheduling — only for 1:1 meetings
    requested_start_time = models.DateTimeField(
        _("Requested start time"),
        null=True,
        blank=True,
        help_text=_(
            "The start time requested by the support seeker for a 1:1 meeting.",
        ),
    )
    requested_duration_minutes = models.PositiveIntegerField(
        _("Requested duration (minutes)"),
        null=True,
        blank=True,
        validators=[
            MinValueValidator(MIN_DURATION_MINUTES),
            MaxValueValidator(MAX_DURATION_MINUTES),
        ],
        help_text=_("The duration requested by the support seeker (5-120 minutes)."),
    )

    # Meeting link — auto-populated via the configured provider if left empty
    meeting_link = models.URLField(
        _("Meeting link"),
        blank=True,
        help_text=_(
            "Auto-populated with a meeting link close to the time of the "
            "event if left empty. Only valid for 1:1 meetings.",
        ),
    )
    provider_room_id = models.CharField(
        _("Provider room ID"),
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "requested_start_time"],
                name="%(app_label)s_%(class)s_unique_session_per_booking",
            ),
        ]

    def __str__(self):
        return f"Request for {self.meeting} by {self.support_seeker}"

    def save(self, *args, **kwargs):
        validate = kwargs.pop("validate", True)
        if validate:
            self.full_clean()
        super().save(*args, **kwargs)

    @property
    def requires_approval(self) -> bool:
        return self.meeting.requires_approval

    @property
    def requires_payment_before_join(self) -> bool:
        return self.meeting.requires_payment_before_join

    @property
    def allows_join_before_payment(self) -> bool:
        return self.meeting.allows_payment_after_join and self.status in {
            MeetingRequestStatus.APPROVED,
            MeetingRequestStatus.PENDING_PAYMENT,
        }

    @property
    def can_join(self) -> bool:
        if self.status in {
            MeetingRequestStatus.PAID,
            MeetingRequestStatus.APPROVED,
        }:
            return True
        return self.allows_join_before_payment

    @property
    def can_pay(self) -> bool:
        return self.status in {
            MeetingRequestStatus.PENDING_PAYMENT,
            MeetingRequestStatus.APPROVED,
        }

    def start(self):
        """Set the request status from the meeting's approval policy."""
        self.__dict__["status"] = self.meeting.initial_request_status

    def clean(self):
        super().clean()
        errors = {}

        if (
            self.meeting
            and self.meeting.meeting_type == MeetingType.ONE_ON_ONE
            and self.requested_start_time
            and self.meeting.created_at
        ):
            min_start_time = self.meeting.created_at + timedelta(minutes=10)
            if self.requested_start_time < min_start_time:
                errors["requested_start_time"] = _(
                    "Requested start time must be at least 10 minutes after "
                    "the meeting's creation time.",
                )

        if errors:
            raise ValidationError(errors)

    @transition(
        field=status,
        source=MeetingRequestStatus.PENDING_APPROVAL,
        target=GET_STATE(_approval_target),
    )
    def approve(self):
        pass

    @transition(
        field=status,
        source=MeetingRequestStatus.PENDING_APPROVAL,
        target=MeetingRequestStatus.REJECTED,
    )
    def reject(self):
        pass

    @transition(
        field=status,
        source=[MeetingRequestStatus.APPROVED, MeetingRequestStatus.PENDING_PAYMENT],
        target=MeetingRequestStatus.PAID,
    )
    def mark_paid(self):
        pass

    @transition(
        field=status,
        source=MeetingRequestStatus.PAID,
        target=MeetingRequestStatus.COMPLETED,
    )
    def complete(self):
        pass

    @transition(
        field=status,
        source=[
            MeetingRequestStatus.PENDING_APPROVAL,
            MeetingRequestStatus.APPROVED,
            MeetingRequestStatus.PAID,
            MeetingRequestStatus.PENDING_PAYMENT,
        ],
        target=MeetingRequestStatus.CANCELLED,
    )
    def cancel(self):
        pass

    def create_checkout_session(self, request):
        """Create a Checkout Session for this request via the charge strategy."""
        from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415
        from neuromancers_network.payments.charges import (  # noqa: PLC0415
            adaptive_pricing as resolve_adaptive_pricing,
        )
        from neuromancers_network.payments.charges import (  # noqa: PLC0415
            build_charge_plan,
        )
        from neuromancers_network.peers.services import (  # noqa: PLC0415
            is_eligible_peer,
        )

        stripe_settings = StripeSettings.load(request)
        if not stripe_settings.secret_key:
            message = "Stripe secret key is not configured"
            raise ValueError(message)

        if not is_eligible_peer(self.meeting.peer):
            message = "The care provider is not currently eligible for bookings"
            raise ValueError(message)

        if self.status not in {
            MeetingRequestStatus.APPROVED,
            MeetingRequestStatus.PENDING_PAYMENT,
        }:
            message = "Request is not ready for payment"
            raise ValueError(message)

        if self.requested_duration_minutes:
            amount = self.meeting.price_for(self.requested_duration_minutes)
        else:
            amount = self.meeting.price
        if amount is None or amount <= 0:
            message = "Meeting price is required for checkout"
            raise ValueError(message)

        currency = self.meeting.currency.lower()
        amount_minor = int(amount * 100)
        peer_profile = getattr(self.meeting.peer, "payment_profile", None)
        destination = (
            peer_profile.stripe_connect_account_id_id
            if peer_profile is not None
            else None
        )
        plan = build_charge_plan(
            amount_minor=amount_minor,
            destination=destination,
            stripe_settings=stripe_settings,
        )
        adaptive_pricing = resolve_adaptive_pricing(request)

        session_kwargs = {
            "mode": "payment",
            "success_url": request.build_absolute_uri("/pay/success/"),
            "cancel_url": request.build_absolute_uri("/pay/cancelled/"),
            "line_items": [
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {"name": self.meeting.title},
                        "unit_amount": amount_minor,
                    },
                    "quantity": 1,
                },
            ],
            "metadata": {
                "meeting_request_id": str(self.pk),
            },
        }
        if adaptive_pricing:
            session_kwargs["adaptive_pricing"] = adaptive_pricing
        if plan.payment_intent_data:
            session_kwargs["payment_intent_data"] = plan.payment_intent_data
        if plan.automatic_tax:
            session_kwargs["automatic_tax"] = plan.automatic_tax
        if plan.stripe_account:
            session_kwargs["stripe_account"] = plan.stripe_account

        stripe.api_key = stripe_settings.secret_key
        session = stripe.checkout.Session.create(**session_kwargs)
        StripeSession.sync_from_stripe_data(session, api_key=stripe_settings.secret_key)
        self.stripe_checkout_session_id = session.id
        self.__dict__["status"] = MeetingRequestStatus.PENDING_PAYMENT
        self.save(validate=False)
        return session.url

    def sync_payment_from_checkout(
        self,
        session_id: str,
        payment_intent_id: str | None,
        amount_total: int | None,
    ) -> None:
        """Synchronize local payment fields after checkout completion."""
        from neuromancers_network.payments.services import (  # noqa: PLC0415
            receipt_url_for,
        )

        self.stripe_checkout_session_id = session_id
        if payment_intent_id:
            self.stripe_payment_intent_id = payment_intent_id
            self.receipt_url = receipt_url_for(payment_intent_id) or self.receipt_url
        if amount_total is not None:
            self.price_paid = Decimal(amount_total) / Decimal(100)
        if can_proceed(self.mark_paid):
            self.mark_paid()
        self.save(validate=False)

    def request_refund(self, reason: str, amount=None):
        """Create a refund request for this meeting request."""
        from neuromancers_network.meetings.models import RefundRequest  # noqa: PLC0415

        refund_request, _created = RefundRequest.objects.get_or_create(
            meeting_request=self,
            defaults={"reason": reason},
        )
        if refund_request.reason != reason:
            refund_request.reason = reason
            refund_request.save(update_fields=["reason", "updated_at"])
        return refund_request.request_refund(amount=amount)

    def populate_meeting_link(self):
        """
        Create a meeting room and populate meeting_link + provider_room_id.

        Called by Celery task close to meeting time, or manually. Only
        applicable to 1:1 meetings.
        """
        from neuromancers_network.core.apis import meeting_room_prefix  # noqa: PLC0415
        from neuromancers_network.core.meeting_providers import (  # noqa: PLC0415
            get_provider,
        )

        start = self.requested_start_time
        duration = self.requested_duration_minutes
        if not start or not duration or self.meeting_link:
            return

        end_date = start + timedelta(minutes=duration)
        result = get_provider().create_room(
            start_at=start,
            end_at=end_date,
            prefix=meeting_room_prefix(),
        )
        self.meeting_link = result.room_url
        self.provider_room_id = result.room_id
        self.save(validate=False, update_fields=["meeting_link", "provider_room_id"])
