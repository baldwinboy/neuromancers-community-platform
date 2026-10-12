from decimal import Decimal

import stripe
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import FSMModelMixin
from django_fsm import transition
from djstripe.models import Session as StripeSession

from neuromancers_network.core.models.base import Timestamped

from .choices import BookingStatus


class Booking(FSMModelMixin, Timestamped):
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
    receipt_url = models.URLField(
        _("Receipt URL"),
        max_length=500,
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

    def record_receipt(self) -> None:
        """Store the Stripe hosted receipt URL for the paid booking, if any."""
        from neuromancers_network.payments.services import (  # noqa: PLC0415
            receipt_url_for,
        )

        url = receipt_url_for(self.stripe_payment_intent_id)
        if url and url != self.receipt_url:
            self.receipt_url = url
            self.save(update_fields=["receipt_url", "updated_at"])

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
        """Create a Checkout Session for this booking (one per peer in a cart)."""
        return create_checkout_session_for_bookings([self], request)


def _line_item(meeting, amount_minor: int) -> dict:
    return {
        "price_data": {
            "currency": meeting.currency.lower(),
            "product_data": {"name": meeting.title},
            "unit_amount": amount_minor,
        },
        "quantity": 1,
    }


def _group_by_peer(bookings) -> dict:
    grouped: dict[int, list[Booking]] = {}
    for booking in bookings:
        grouped.setdefault(booking.meeting.peer_id, []).append(booking)
    return grouped


def _peer_session_kwargs(peer_bookings, request, stripe_settings, adaptive_pricing):
    """Build Checkout kwargs for one peer's group of bookings."""
    from neuromancers_network.payments.charges import build_charge_plan  # noqa: PLC0415
    from neuromancers_network.peers.services import is_eligible_peer  # noqa: PLC0415

    meeting = peer_bookings[0].meeting
    if not is_eligible_peer(meeting.peer):
        message = "The care provider is not currently eligible for bookings"
        raise ValueError(message)

    line_items = []
    total_minor = 0
    for booking in peer_bookings:
        amount = (
            booking.total_amount
            if booking.total_amount is not None
            else booking.compute_total()
        )
        if not amount or amount <= 0:
            message = "Booking has no amount to charge"
            raise ValueError(message)
        amount_minor = int(amount * 100)
        total_minor += amount_minor
        booking.total_amount = amount
        line_items.append(_line_item(meeting, amount_minor))

    peer_profile = getattr(meeting.peer, "payment_profile", None)
    destination = (
        peer_profile.stripe_connect_account_id_id if peer_profile is not None else None
    )
    plan = build_charge_plan(
        amount_minor=total_minor,
        destination=destination,
        stripe_settings=stripe_settings,
    )

    session_kwargs = {
        "mode": "payment",
        "adaptive_pricing": adaptive_pricing,
        "success_url": request.build_absolute_uri("/pay/success/"),
        "cancel_url": request.build_absolute_uri("/pay/cancelled/"),
        "line_items": line_items,
        "metadata": {
            "booking_ids": ",".join(str(booking.pk) for booking in peer_bookings),
        },
    }
    if plan.payment_intent_data:
        session_kwargs["payment_intent_data"] = plan.payment_intent_data
    if plan.automatic_tax:
        session_kwargs["automatic_tax"] = plan.automatic_tax
    if plan.stripe_account:
        session_kwargs["stripe_account"] = plan.stripe_account
    return session_kwargs


def create_checkout_session_for_bookings(bookings, request) -> str:
    """Create one Checkout Session per peer for *bookings*; return the first URL.

    Bookings are grouped by care provider; each group becomes a single session
    on that provider's connected account (per the charge strategy). Every
    booking stores the resulting session id.
    """
    from neuromancers_network.core.models import LocalizationSettings  # noqa: PLC0415
    from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415

    bookings = list(bookings)
    if not bookings:
        message = "No bookings to pay for"
        raise ValueError(message)

    stripe_settings = StripeSettings.load(request)
    if not stripe_settings.is_ready:
        message = "Stripe is not configured"
        raise ValueError(message)

    adaptive_pricing = None
    if LocalizationSettings.load(request).exchange_rate_source == "stripe":
        adaptive_pricing = {"enabled": True}

    stripe.api_key = stripe_settings.secret_key
    first_url = None
    for peer_bookings in _group_by_peer(bookings).values():
        session_kwargs = _peer_session_kwargs(
            peer_bookings,
            request,
            stripe_settings,
            adaptive_pricing,
        )
        session = stripe.checkout.Session.create(**session_kwargs)
        StripeSession.sync_from_stripe_data(
            session,
            api_key=stripe_settings.secret_key,
        )
        for booking in peer_bookings:
            booking.stripe_checkout_session_id = session.id
            booking.save(
                update_fields=[
                    "stripe_checkout_session_id",
                    "total_amount",
                    "updated_at",
                ],
            )
        if first_url is None:
            first_url = session.url
    return first_url
