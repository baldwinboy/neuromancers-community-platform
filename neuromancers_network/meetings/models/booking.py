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

    @property
    def display_title(self) -> str:
        return f"Booking #{self.pk}"

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
        from neuromancers_network.payments.services import receipt_url_for  # noqa: PLC0415

        url = receipt_url_for(self.stripe_payment_intent_id)
        if url and url != self.receipt_url:
            self.receipt_url = url
            self.save(update_fields=["receipt_url", "updated_at"])

    def compute_total(self) -> Decimal:
        """Sum the priced sessions, or the meeting price when there are none.

        Raises ``ValueError`` when a price cannot be resolved, so a cart is never
        charged zero for a misconfigured meeting.
        """
        sessions = list(self.sessions.order_by("pk"))
        if not sessions:
            price = self.meeting.price
            if price is None or price <= 0:
                message = "Booking has no amount to charge"
                raise ValueError(message)
            return price
        return sum((_session_amount(session) for session in sessions), Decimal("0"))

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


def _session_amount(session) -> Decimal:
    """Return the priced amount for *session*, or raise when it is unknown."""
    meeting = session.meeting
    duration = session.requested_duration_minutes or meeting.duration_minutes
    amount = meeting.price_for(duration) if duration else meeting.price
    if amount is None or amount <= 0:
        message = "Session has no resolvable price to charge"
        raise ValueError(message)
    return amount


def _group_by_peer_currency(bookings) -> dict[tuple[int, str], list[Booking]]:
    """Group bookings by care provider and currency (one Checkout each)."""
    grouped: dict[tuple[int, str], list[Booking]] = {}
    for booking in bookings:
        meeting = booking.meeting
        key = (meeting.peer_id, meeting.currency.upper())
        grouped.setdefault(key, []).append(booking)
    return grouped


def _booking_items(booking) -> list[tuple]:
    """Return ``(meeting, amount, ref)`` for each chargeable item in *booking*."""
    sessions = list(booking.sessions.order_by("pk"))
    if sessions:
        items = []
        booking_total = Decimal("0")
        for session in sessions:
            amount = _session_amount(session)
            booking_total += amount
            items.append((session.meeting, amount, f"request:{session.pk}"))
        booking.total_amount = booking_total
        return items

    amount = booking.total_amount or booking.compute_total()
    if not amount or amount <= 0:
        message = "Booking has no amount to charge"
        raise ValueError(message)
    booking.total_amount = amount
    return [(booking.meeting, amount, f"booking:{booking.pk}")]


def _peer_session_kwargs(peer_bookings, request, stripe_settings, adaptive_pricing):
    """Build Checkout kwargs for one peer's group of bookings.

    One line item is created per session request (and per session-less booking),
    with ``line_item_refs`` recording the matching records in the same order so
    the webhook can apply Stripe's per-item amount back onto the right row.
    """
    from neuromancers_network.payments.charges import build_charge_plan  # noqa: PLC0415
    from neuromancers_network.peers.services import is_eligible_peer  # noqa: PLC0415

    meeting = peer_bookings[0].meeting
    if not is_eligible_peer(meeting.peer):
        message = "The care provider is not currently eligible for bookings"
        raise ValueError(message)

    line_items: list[dict] = []
    line_item_refs: list[str] = []
    currencies: set[str] = set()
    total_minor = 0

    for booking in peer_bookings:
        for item_meeting, amount, ref in _booking_items(booking):
            amount_minor = int(amount * 100)
            currencies.add(item_meeting.currency.upper())
            total_minor += amount_minor
            line_items.append(_line_item(item_meeting, amount_minor))
            line_item_refs.append(ref)

    if len(currencies) > 1:
        message = "A checkout session cannot mix currencies"
        raise ValueError(message)

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
        "success_url": request.build_absolute_uri("/pay/success/"),
        "cancel_url": request.build_absolute_uri("/pay/cancelled/"),
        "line_items": line_items,
        "metadata": {
            "booking_ids": ",".join(str(booking.pk) for booking in peer_bookings),
            "line_item_refs": ",".join(line_item_refs),
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
    return session_kwargs


def create_checkout_session_for_bookings(bookings, request) -> str:
    """Create one Checkout Session for *bookings* and return its URL.

    A session can only charge one care provider in one currency, so callers must
    supply bookings from a single ``(peer, currency)`` group. Every booking
    stores the resulting session id.
    """
    from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415
    from neuromancers_network.payments.charges import (  # noqa: PLC0415
        adaptive_pricing as resolve_adaptive_pricing,
    )

    bookings = list(bookings)
    if not bookings:
        message = "No bookings to pay for"
        raise ValueError(message)
    groups = _group_by_peer_currency(bookings)
    if len(groups) > 1:
        message = "A checkout can only include one care provider and currency"
        raise ValueError(message)
    peer_bookings = next(iter(groups.values()))

    stripe_settings = StripeSettings.load(request)
    if not stripe_settings.is_ready:
        message = "Stripe is not configured"
        raise ValueError(message)

    adaptive_pricing = resolve_adaptive_pricing(request)

    stripe.api_key = stripe_settings.secret_key
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
    if not session.url:
        message = "Stripe did not return a checkout URL"
        raise ValueError(message)
    return session.url
