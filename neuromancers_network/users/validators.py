"""Username moderation backed by :class:`ModerationSettings`.

The admin-curated blocklist is read through a short-lived cache so sign-up and
social flows can call it freely. The cache is busted by ``core.signals`` whenever
the settings row changes.
"""

from __future__ import annotations

import re

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

CACHE_KEY = "neuromancers_network.blocked_usernames"
CACHE_TTL = 300


def _moderation_config():
    from neuromancers_network.core.models import ModerationSettings  # noqa: PLC0415

    try:
        return ModerationSettings.load()
    except Exception:  # noqa: BLE001 - table may not exist yet
        return None


def blocked_usernames() -> list[str]:
    """Return the (normalised) blocklist entries, cached for ``CACHE_TTL``."""
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    config = _moderation_config()
    entries: list[str] = []
    if config is not None and config.username_blocklist:
        entries = [
            line.strip()
            for line in config.username_blocklist.splitlines()
            if line.strip()
        ]
        if not config.username_case_sensitive:
            entries = [entry.lower() for entry in entries]
    cache.set(CACHE_KEY, entries, CACHE_TTL)
    return entries


def bust_blocked_usernames_cache(*args, **kwargs) -> None:
    """Drop the cached blocklist (called on settings save/delete)."""
    cache.delete(CACHE_KEY)


def validate_username_not_blocked(value: str | None) -> None:
    """Raise ``ValidationError`` when *value* is on the admin blocklist."""
    if not value:
        return

    config = _moderation_config()
    if config is None:
        return

    candidate = value if config.username_case_sensitive else value.lower()
    for entry in blocked_usernames():
        matched = (
            re.fullmatch(entry, candidate)
            if config.username_blocklist_use_regex
            else candidate == entry
        )
        if matched:
            raise ValidationError(
                _("This username is not allowed."),
                code="username_blocked",
            )
