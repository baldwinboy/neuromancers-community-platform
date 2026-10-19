"""Keep :class:`PeerSubscription` in sync with dj-stripe subscriptions.

A user is granted peer standing when they subscribe to one of the Stripe Prices
configured in :class:`PeerRequirementsSettings.peer_plan_price_ids`.
"""

from __future__ import annotations

import logging

from django.db import DatabaseError
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.utils import timezone
from djstripe.enums import SubscriptionStatus
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Subscription as StripeSubscription

from neuromancers_network.payments.models import PaymentProfile
from neuromancers_network.peers.models import PeerSubscription
from neuromancers_network.peers.models.settings import PeerRequirementsSettings
from neuromancers_network.peers.services import enforce_subscription_lapse

logger = logging.getLogger(__name__)

SUBSCRIPTION_EVENTS = [
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "customer.subscription.paused",
    "customer.subscription.resumed",
]


def _peer_plan_price_ids() -> set[str]:
    try:
        settings_obj = PeerRequirementsSettings.load()
    except DatabaseError:
        logger.debug("PeerRequirementsSettings unavailable", exc_info=True)
        return set()
    return set(settings_obj.peer_plan_price_ids or [])


def _remove_peer_subscription(existing, payment_profile) -> None:
    if existing is None:
        return
    existing.delete()
    _safe(enforce_subscription_lapse, payment_profile)


def _subscription_price_ids(data: dict) -> set[str]:
    items = data.get("items", {}).get("data", []) or []
    price_ids: set[str] = set()
    for item in items:
        price_id = (item.get("price") or {}).get("id")
        if price_id:
            price_ids.add(price_id)
    return price_ids


@djstripe_receiver(SUBSCRIPTION_EVENTS)
def sync_peer_subscription(sender, event, **kwargs):
    """Create/update/remove a ``PeerSubscription`` from a Stripe event."""
    data = event.data.get("object", {})
    subscription_id = data.get("id")
    if not subscription_id:
        return

    stripe_subscription = StripeSubscription.sync_from_stripe_data(
        data,
        api_key=event.default_api_key,
    )

    customer_id = data.get("customer")
    payment_profile = PaymentProfile.objects.filter(
        stripe_customer_id_id=customer_id,
    ).first()
    if payment_profile is None:
        logger.debug("No payment profile for customer %s", customer_id)
        return

    existing = PeerSubscription.objects.filter(
        payment_profile=payment_profile,
    ).first()

    status = data.get("status")
    removed = event.type == "customer.subscription.deleted" or status == "canceled"
    is_peer_plan = bool(_subscription_price_ids(data) & _peer_plan_price_ids())

    if removed or not is_peer_plan:
        _remove_peer_subscription(existing, payment_profile)
        return

    if status in {SubscriptionStatus.past_due, SubscriptionStatus.unpaid}:
        _safe(enforce_subscription_lapse, payment_profile)
        return

    # Pausing collection leaves the Stripe status unchanged, so pause state is
    # tracked separately from the status.
    paused = bool(data.get("pause_collection"))
    now = timezone.now()

    if existing is None:
        PeerSubscription.objects.create(
            payment_profile=payment_profile,
            subscription=stripe_subscription,
            paused_at=now if paused else None,
        )
        return

    updates: list[str] = []
    if existing.subscription_id != stripe_subscription.pk:
        existing.subscription = stripe_subscription
        updates.append("subscription")
    if paused and existing.paused_at is None:
        existing.paused_at = now
        updates.append("paused_at")
        _safe(enforce_subscription_lapse, payment_profile)
    elif not paused and existing.paused_at is not None:
        existing.paused_at = None
        updates.append("paused_at")
    if updates:
        existing.save(update_fields=[*updates, "updated_at"])


@djstripe_receiver(["invoice.payment_succeeded", "invoice.paid"])
def record_subscription_invoice(sender, event, **kwargs):
    """Record paid invoices on the subscription-revenue ledger."""
    from neuromancers_network.analytics.services import (  # noqa: PLC0415
        occurred_at_from,
    )
    from neuromancers_network.analytics.services import (  # noqa: PLC0415
        record_subscription_payment,
    )

    data = event.data.get("object", {})
    invoice_id = data.get("id")
    amount_paid = data.get("amount_paid") or 0
    if not invoice_id or amount_paid <= 0:
        return

    payment_profile = PaymentProfile.objects.filter(
        stripe_customer_id_id=data.get("customer"),
    ).first()
    record_subscription_payment(
        invoice_id=invoice_id,
        subscription_id=data.get("subscription") or "",
        amount_minor=amount_paid,
        currency=data.get("currency") or "GBP",
        occurred_at=occurred_at_from(data),
        payer=payment_profile.user if payment_profile is not None else None,
    )


# --- Calendar event sync ----------------------------------------------------


def _safe(func, *args):
    try:
        func(*args)
    except Exception:
        logger.exception("Calendar sync failed for %s", func.__name__)


def connect_calendar_signals() -> None:
    """Keep ``CalendarEvent`` rows in sync with their source objects."""
    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415
    from neuromancers_network.peers import calendar  # noqa: PLC0415
    from neuromancers_network.peers.models import PeerAvailability  # noqa: PLC0415

    def on_availability(sender, instance, **kwargs):
        _safe(calendar.sync_availability, instance)

    def on_availability_delete(sender, instance, **kwargs):
        _safe(calendar.remove_events, "availability", instance.pk)

    def on_request(sender, instance, **kwargs):
        _safe(calendar.sync_request, instance)

    def on_request_delete(sender, instance, **kwargs):
        _safe(calendar.remove_events, "request", instance.pk)

    def on_meeting(sender, instance, **kwargs):
        _safe(calendar.sync_meeting, instance)

    def on_meeting_delete(sender, instance, **kwargs):
        _safe(calendar.remove_events, "meeting", instance.pk)

    post_save.connect(
        on_availability,
        sender=PeerAvailability,
        dispatch_uid="peers.calendar.availability.save",
        weak=False,
    )
    post_delete.connect(
        on_availability_delete,
        sender=PeerAvailability,
        dispatch_uid="peers.calendar.availability.delete",
        weak=False,
    )
    post_save.connect(
        on_request,
        sender=MeetingRequest,
        dispatch_uid="peers.calendar.request.save",
        weak=False,
    )
    post_delete.connect(
        on_request_delete,
        sender=MeetingRequest,
        dispatch_uid="peers.calendar.request.delete",
        weak=False,
    )
    post_save.connect(
        on_meeting,
        sender=Meeting,
        dispatch_uid="peers.calendar.meeting.save",
        weak=False,
    )
    post_delete.connect(
        on_meeting_delete,
        sender=Meeting,
        dispatch_uid="peers.calendar.meeting.delete",
        weak=False,
    )


connect_calendar_signals()
