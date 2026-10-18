"""Active-session helpers for the DB-backed session store."""

from __future__ import annotations

import logging

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_ACTIVE_SESSION_KEYS = 100


def active_session_keys(user) -> list[str]:
    """Session keys owned by *user*, capped at ``MAX_ACTIVE_SESSION_KEYS``.

    The DB session store has no user index, so keys are found by decoding
    non-expired rows. Results are streamed and capped; truncation is logged.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    keys = []
    sessions = (
        Session.objects.filter(expire_date__gte=timezone.now())
        .order_by("-expire_date")
        .iterator(chunk_size=500)
    )
    for session in sessions:
        data = session.get_decoded()
        if str(data.get(SESSION_KEY)) == str(user.pk):
            keys.append(session.session_key)
            if len(keys) >= MAX_ACTIVE_SESSION_KEYS:
                logger.warning(
                    "Capped active session keys at %s for user %s",
                    MAX_ACTIVE_SESSION_KEYS,
                    user.pk,
                )
                break
    return keys


def revoke_sessions(user, *, keep_current: str | None = None) -> int:
    """Delete *user*'s sessions, optionally sparing the current one."""
    keys = [key for key in active_session_keys(user) if key != keep_current]
    if not keys:
        return 0
    deleted, _ = Session.objects.filter(session_key__in=keys).delete()
    return deleted
