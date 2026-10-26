"""Signed links for cancelling a pending account deletion."""

from __future__ import annotations

import time
from datetime import timedelta

from django.core import signing
from django.urls import reverse

SALT = "moderation.account-deletion.cancel"
MAX_AGE_SECONDS = 60 * 60 * 24 * 90


def deletion_cancel_token(deletion) -> str:
    """Sign a cancellation token for *deletion*."""
    expires_at = deletion.scheduled_for + timedelta(days=1)
    return signing.dumps(
        {
            "deletion_id": deletion.pk,
            "user_id": deletion.user_id,
            "exp": int(expires_at.timestamp()),
        },
        salt=SALT,
        compress=True,
    )


def read_deletion_cancel_token(token: str) -> dict | None:
    """Return the validated token payload, or ``None`` when invalid/expired."""
    try:
        payload = signing.loads(token, salt=SALT, max_age=MAX_AGE_SECONDS)
    except signing.BadSignature:
        return None
    if not isinstance(payload, dict):
        return None
    try:
        payload = {
            "deletion_id": int(payload["deletion_id"]),
            "user_id": int(payload["user_id"]),
            "exp": int(payload["exp"]),
        }
    except KeyError, TypeError, ValueError:
        return None
    if payload["exp"] < int(time.time()):
        return None
    return payload


def deletion_cancel_url(deletion, *, request=None) -> str:
    """Return an absolute cancellation URL for *deletion*."""
    path = reverse(
        "account_deletion_cancel",
        args=[deletion_cancel_token(deletion)],
    )
    if request is not None:
        return request.build_absolute_uri(path)
    from wagtail.models import Site  # noqa: PLC0415

    site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()
    if site is None:
        return path
    return f"{site.root_url.rstrip('/')}{path}"
