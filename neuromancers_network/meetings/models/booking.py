from decimal import Decimal

import stripe
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import transition
from djstripe.models import Session as StripeSession

from neuromancers_network.core.models.base import Timestamped

from .choices import BookingStatus


class Booking(Timestamped):
    """A seeker's purchase of one or more sessions of a meeting."""

    meeting = models.ForeignKey(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    support_seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    status = FSMField(
        _("Status"),
        default=BookingStatus.PENDING,
        choices=BookingStatus.choices,
    )
    total_amount = models.DecimalField(
        _("Total amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(_("Currency"), max_length=3, default="GBP")
    stripe_checkout_session_id = models.CharField(
        _("Stripe checkout session ID"),
        max_length=255,
        blank=True,
    )
    stripe_payment_intent_id = models.CharField(
        _("Stripe payment intent ID"),
        max_length=255,
        blank=True,
    )
    access_needs = models.TextField(_("Access needs"), blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Booking")
        verbose_name_plural = _("Bookings")

    def __str__(self):
        return f"Booking #{self.pk} for {self.meeting}"

    @transition(
        field=status,
        source=BookingStatus.PENDING,
        target=BookingStatus.PAID,
    )
    def mark_paid(self):
        pass

    @transition(
        field=status,
        source=[BookingStatus.PENDING, BookingStatus.PAID],
        target=BookingStatus.CANCELLED,
    )
    def cancel(self):
        pass

    @transition(
        field=status,
        source=BookingStatus.PAID,
        target=BookingStatus.REFUNDED,
    )
    def refund(self):
        pass

    def compute_total(self) -> Decimal:
        """Compute the booking total from its sessions (falling back to price)."""
        sessions = list(self.sessions.all())
        if not sessions:
            return self.meeting.price or Decimal("0")
        total = Decimal("0")
        for session in sessions:
            duration = (
                session.requested_duration_minutes or self.meeting.duration_minutes
            )
            price = self.meeting.price_for(duration) if duration else self.meeting.price
            total += price or Decimal("0")
        return total

    def create_checkout_session(self, request):
        """Create a destination-charge Checkout Session for this booking."""
        from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415

        stripe_settings = StripeSettings.load(request)
        if not stripe_settings.is_ready:
            message = "Stripe is not configured"
            raise ValueError(message)

        peer_profile = getattr(self.meeting.peer, "payment_profile", None)
        destination = (
            peer_profile.stripe_connect_account_id_id
            if peer_profile is not None
            else None
        )
        if not destination:
            message = "Peer has no connected Stripe account"
            raise ValueError(message)

        amount = (
            self.total_amount if self.total_amount is not None else self.compute_total()
        )
        if not amount or amount <= 0:
            message = "Booking has no amount to charge"
            raise ValueError(message)

        amount_minor = int(amount * 100)
        fee_percent = stripe_settings.application_fee or 0
        application_fee_amount = round(amount_minor * fee_percent / 100)

        from neuromancers_network.core.models import (  # noqa: PLC0415
            LocalizationSettings,
        )

        adaptive_pricing = None
        if LocalizationSettings.load(request).exchange_rate_source == "stripe":
            adaptive_pricing = {"enabled": True}

        stripe.api_key = stripe_settings.secret_key
        session = stripe.checkout.Session.create(
            mode="payment",
            adaptive_pricing=adaptive_pricing,
            success_url=request.build_absolute_uri("/pay/success/"),
            cancel_url=request.build_absolute_uri("/pay/cancelled/"),
            line_items=[
                {
                    "price_data": {
                        "currency": self.meeting.currency.lower(),
                        "product_data": {"name": self.meeting.title},
                        "unit_amount": amount_minor,
                    },
                    "quantity": 1,
                },
            ],
            payment_intent_data={
                "application_fee_amount": application_fee_amount,
                "transfer_data": {"destination": destination},
            },
            metadata={"booking_id": str(self.pk)},
        )
        StripeSession.sync_from_stripe_data(
            session,
            api_key=stripe_settings.secret_key,
        )
        self.stripe_checkout_session_id = session.id
        self.total_amount = amount
        self.save(
            update_fields=[
                "stripe_checkout_session_id",
                "total_amount",
                "updated_at",
            ],
        )
        return session.url
