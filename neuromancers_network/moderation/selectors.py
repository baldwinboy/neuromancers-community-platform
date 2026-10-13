"""Context-model selectors for moderation feeds."""

from __future__ import annotations


def blocked_users(request=None, page=None):
    """Members the signed-in member has blocked (an unblock-list feed)."""
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return get_user_model().objects.none()
    return get_user_model().objects.filter(blocks_received__blocker=user)
