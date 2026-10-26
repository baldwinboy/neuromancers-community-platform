"""Notification delivery policy helpers."""

from __future__ import annotations

from django.db import DatabaseError

#: Event types that are always delivered, regardless of opt-out settings.
TRANSACTIONAL_EVENT_TYPES = frozenset(
    {
        "account_created",
        "account_deleted",
        "account_deactivated",
        "account_reactivated",
        "account_deletion_scheduled",
        "account_deletion_cancelled",
        "booking_paid",
        "booking_cancelled",
        "refund_approved",
        "refund_rejected",
        "refund_refunded",
        "subscription_created",
        "subscription_cancelled",
        "subscription_paused",
        "subscription_resumed",
        "payment_succeeded",
        "payment_failed",
        "ip_banned",
        "ip_unbanned",
        "email_banned",
        "email_unbanned",
        "report_resolved",
        "data_export_ready",
    },
)


def _notification_policy() -> tuple[set[str], set[str]]:
    """Return (transactional, default_disabled) for the current policy."""
    transactional = set(TRANSACTIONAL_EVENT_TYPES)
    default_disabled: set[str] = set()
    try:
        from neuromancers_network.core.models import NotificationSettings  # noqa: PLC0415

        settings_obj = NotificationSettings.load()
        transactional |= set(settings_obj.transactional_events or [])
        default_disabled = set(settings_obj.default_disabled_event_types or [])
    except DatabaseError:
        pass
    return transactional, default_disabled


def effective_transactional_event_types() -> set[str]:
    """The fixed transactional events plus admin-added transactional events."""
    return _notification_policy()[0]


def member_optout_choices():
    """Event choices a member can actually opt out of."""
    from neuromancers_network.inbox.models import NotificationEventType  # noqa: PLC0415

    transactional = effective_transactional_event_types()
    return [
        (value, label)
        for value, label in NotificationEventType.choices
        if value not in transactional
    ]


def should_notify(user, event_type: str) -> bool:
    """Whether *user* should receive a notification for *event_type*.

    Transactional events are always delivered. Otherwise a member's personal
    opt-out list wins, falling back to the admin default disabled list.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    transactional, default_disabled = _notification_policy()
    if event_type in transactional:
        return True

    preference = getattr(user, "notification_preference", None)
    if preference is not None and event_type in set(
        preference.disabled_event_types or [],
    ):
        return False

    return event_type not in default_disabled
