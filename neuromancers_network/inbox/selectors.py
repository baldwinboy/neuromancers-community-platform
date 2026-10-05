"""Query helpers for daisIE context models."""

from __future__ import annotations


def user_notification_preference(request=None, page=None):
    """The signed-in member's notification preference, if any."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    from neuromancers_network.inbox.models import (  # noqa: PLC0415
        NotificationPreference,
    )

    return NotificationPreference.objects.filter(user=user).first()
