"""Hashed identity records that enforce re-registration cooldowns."""

from __future__ import annotations

import hashlib
from datetime import timedelta

from django.utils import timezone


def _hash(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def email_hash(email: str) -> str:
    return _hash(email)


def username_hash(username: str) -> str:
    return _hash(username)


def record_deleted_identity(
    *,
    email: str,
    username: str,
    cooldown_days: int,
) -> None:
    """Store the (hashed) identity of a purged account for the cooldown window."""
    from .models import DeletedIdentity  # noqa: PLC0415

    DeletedIdentity.objects.create(
        email_hash=email_hash(email),
        username_hash=username_hash(username),
        purge_after=timezone.now() + timedelta(days=max(0, cooldown_days)),
    )


def sweep_deleted_identities(now=None) -> int:
    """Delete cooldown records whose retention window has elapsed."""
    from .models import DeletedIdentity  # noqa: PLC0415

    now = now or timezone.now()
    deleted, _ = DeletedIdentity.objects.filter(purge_after__lte=now).delete()
    return deleted


def is_identity_blocked(
    *,
    email: str | None = None,
    username: str | None = None,
) -> bool:
    """Whether *email* or *username* matches a still-cooling deleted identity."""
    from django.db.models import Q  # noqa: PLC0415

    from .models import DeletedIdentity  # noqa: PLC0415

    query = Q()
    if email:
        query |= Q(email_hash=email_hash(email))
    if username:
        query |= Q(username_hash=username_hash(username))
    if not query:
        return False
    return DeletedIdentity.objects.filter(
        query,
        purge_after__gt=timezone.now(),
    ).exists()
