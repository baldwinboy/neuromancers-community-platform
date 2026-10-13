"""Admin-configurable cooldowns for member identity changes.

The windows live on :class:`~neuromancers_network.core.models.AccountSettings`.
Moderators bypass the cooldown so support can act without waiting.
"""

from __future__ import annotations

import math
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def cooldown_remaining(last_changed, days: int) -> timedelta | None:
    """Return the time left in the cooldown, or ``None`` if it has elapsed."""
    if last_changed is None or days <= 0:
        return None
    remaining = timedelta(days=days) - (timezone.now() - last_changed)
    return remaining if remaining > timedelta(0) else None


def _remaining_days(remaining: timedelta) -> int:
    return max(1, math.ceil(remaining.total_seconds() / 86400))


def _account_settings():
    from neuromancers_network.core.models import AccountSettings  # noqa: PLC0415

    try:
        return AccountSettings.load()
    except Exception:  # noqa: BLE001 - settings table may not exist yet
        return None


def _cooldown_days(field: str) -> int:
    settings_obj = _account_settings()
    return int(getattr(settings_obj, field, 0) or 0)


def ensure_username_change_allowed(user) -> None:
    """Raise ``ValidationError`` while the username cooldown is active."""
    if user is None or getattr(user, "is_moderator", False):
        return
    remaining = cooldown_remaining(
        getattr(user, "username_changed_at", None),
        _cooldown_days("username_change_cooldown_days"),
    )
    if remaining is not None:
        raise ValidationError(
            _(
                "You can change your username again in %(days)s day(s).",
            )
            % {"days": _remaining_days(remaining)},
            code="username_cooldown",
        )


def ensure_email_change_allowed(user) -> None:
    """Raise ``ValidationError`` while the email cooldown is active."""
    if user is None or getattr(user, "is_moderator", False):
        return
    remaining = cooldown_remaining(
        getattr(user, "email_changed_at", None),
        _cooldown_days("email_change_cooldown_days"),
    )
    if remaining is not None:
        raise ValidationError(
            _(
                "You can change your email address again in %(days)s day(s).",
            )
            % {"days": _remaining_days(remaining)},
            code="email_cooldown",
        )
