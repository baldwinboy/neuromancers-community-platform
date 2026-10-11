"""Keep :class:`PeerSubscription` in sync with dj-stripe subscriptions.

A user is granted peer standing when they subscribe to one of the Stripe Prices
configured in :class:`PeerRequirementsSettings.peer_plan_price_ids`.
"""

from __future__ import annotations

import logging

from django.db import DatabaseError
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Subscription as StripeSubscription

from neuromancers_network.payments.models import PaymentProfile
from neuromancers_network.peers.models import PeerSubscription
from neuromancers_network.peers.models.settings import PeerRequirementsSettings

logger = logging.getLogger(__name__)

SUBSCRIPTION_EVENTS = [
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
]


def _peer_plan_price_ids() -> set[str]:
    try:
        settings_obj = PeerRequirementsSettings.load()
    except DatabaseError:
        logger.debug("PeerRequirementsSettings unavailable", exc_info=True)
        return set()
    return set(settings_obj.peer_plan_price_ids or [])


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
        if existing is not None:
            existing.delete()
        return

    if existing is None:
        PeerSubscription.objects.create(
            payment_profile=payment_profile,
            subscription=stripe_subscription,
        )
    elif existing.subscription_id != stripe_subscription.pk:
        existing.subscription = stripe_subscription
        existing.save(update_fields=["subscription", "updated_at"])


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
