"""Query helpers for daisIE context models."""

from __future__ import annotations


def user_notification_preference(request=None, page=None):
    """The signed-in member's notification preference, if any."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    from neuromancers_network.inbox.models import NotificationPreference  # noqa: PLC0415

    return NotificationPreference.objects.filter(user=user).first()


def user_notifications(request=None, page=None):
    """The signed-in member's non-deleted in-app notifications."""
    from neuromancers_network.inbox.models import Notification  # noqa: PLC0415

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return Notification.objects.none()
    return Notification.objects.filter(recipient=user, deleted_at__isnull=True)


def notification_unread_query(queryset, params, key):
    """Boolean filter: ``1`` keeps unread, ``0`` keeps read."""
    value = params.get(f"filter_{key}") if params else None
    if value in ("1", "true", "True", "yes", "on"):
        return queryset.filter(read_at__isnull=True)
    if value in ("0", "false", "False", "no", "off"):
        return queryset.filter(read_at__isnull=False)
    return queryset
