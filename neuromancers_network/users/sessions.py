"""Active-session helpers for the DB-backed session store."""

from __future__ import annotations

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.utils import timezone


def active_session_keys(user) -> list[str]:
    """Session keys owned by *user* (decoded from non-expired sessions)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    keys = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get(SESSION_KEY)) == str(user.pk):
            keys.append(session.session_key)
    return keys


def revoke_sessions(user, *, keep_current: str | None = None) -> int:
    """Delete *user*'s sessions, optionally sparing the current one."""
    keys = [key for key in active_session_keys(user) if key != keep_current]
    if not keys:
        return 0
    deleted, _ = Session.objects.filter(session_key__in=keys).delete()
    return deleted
