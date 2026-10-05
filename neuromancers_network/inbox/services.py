"""Notification delivery policy helpers."""

from __future__ import annotations

from django.db import DatabaseError

#: Event types that are always delivered, regardless of opt-out settings.
TRANSACTIONAL_EVENT_TYPES = frozenset(
    {
        "account_created",
        "account_deleted",
        "booking_paid",
        "booking_cancelled",
        "refund_approved",
        "refund_rejected",
        "refund_refunded",
        "subscription_created",
        "subscription_cancelled",
        "payment_succeeded",
        "payment_failed",
    },
)


def should_notify(user, event_type: str) -> bool:
    """Whether *user* should receive a notification for *event_type*.

    Transactional events are always delivered. Otherwise a member's personal
    opt-out list wins, falling back to the admin default disabled list.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    transactional = set(TRANSACTIONAL_EVENT_TYPES)
    default_disabled: set[str] = set()
    try:
        from neuromancers_network.core.models import (  # noqa: PLC0415
            NotificationSettings,
        )

        settings_obj = NotificationSettings.load()
        transactional |= set(settings_obj.transactional_events or [])
        default_disabled = set(settings_obj.default_disabled_event_types or [])
    except DatabaseError:
        pass

    if event_type in transactional:
        return True

    preference = getattr(user, "notification_preference", None)
    if preference is not None and event_type in set(
        preference.disabled_event_types or [],
    ):
        return False

    return event_type not in default_disabled
