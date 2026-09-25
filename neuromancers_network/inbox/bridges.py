"""Shared context/recipient builders for daisIE notification bridges."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from neuromancers_network.inbox.services import should_notify


def context_from_payload(source) -> dict:
    """Expose an inbox payload to a daisIE EmailTemplate as ``payload.*``."""
    return dict(source.get("payload") or {})


def recipients_from_payload(source):
    """Resolve ``recipient_user_ids`` to users, honouring per-user opt-outs."""
    payload = source.get("payload") or {}
    event_type = source.get("event_type") or ""
    ids = [pk for pk in (payload.get("recipient_user_ids") or []) if pk is not None]
    if not ids:
        return []
    user_model = get_user_model()
    users = user_model.objects.filter(pk__in=ids)
    return [user for user in users if should_notify(user, event_type)]
