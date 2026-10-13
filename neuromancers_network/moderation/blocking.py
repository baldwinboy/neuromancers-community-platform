"""Member-to-member blocking services.

Blocking is pairwise and stored one-way per block; the viewer-scoped filtering
that hides each party's content is layered on separately.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.audit import record_audit
from neuromancers_network.inbox.events import emit

from .models import UserBlock

logger = logging.getLogger(__name__)


def _announce(event_type: str, blocker, blocked, *, request=None) -> None:
    try:
        emit(
            event_type,
            payload={
                "actor_user_id": blocker.pk,
                "recipient_user_ids": [blocker.pk],
                "object_type": "userblock",
                "object_id": blocked.pk,
                "meta": {
                    "blocker_user_id": blocker.pk,
                    "blocked_user_id": blocked.pk,
                },
            },
            event_ref=f"user.{blocker.pk}.{event_type}.{blocked.pk}",
        )
    except Exception:
        logger.exception("Failed to emit %s", event_type)
    try:
        record_audit(
            action=f"account.{event_type.removeprefix('user_')}",
            actor=blocker,
            user=blocker,
            request=request,
            event_type=event_type,
            changes={"blocked_user_id": blocked.pk},
        )
    except Exception:
        logger.exception("Failed to audit %s", event_type)


def block_user(blocker, blocked, *, request=None, reason: str = "") -> UserBlock:
    """Create (idempotently) a block from *blocker* on *blocked*."""
    if blocker.pk == blocked.pk:
        raise ValidationError(_("You cannot block yourself."))
    block, created = UserBlock.objects.get_or_create(
        blocker=blocker,
        blocked=blocked,
        defaults={"reason": reason or ""},
    )
    if created:
        _announce("user_blocked", blocker, blocked, request=request)
    return block


def unblock_user(blocker, blocked, *, request=None) -> None:
    """Remove a block (idempotent)."""
    deleted, _ = UserBlock.objects.filter(blocker=blocker, blocked=blocked).delete()
    if deleted:
        _announce("user_unblocked", blocker, blocked, request=request)


def blocked_user_ids(user) -> set[int]:
    """IDs of the members *user* has blocked (for viewer-scoped filtering)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    return set(
        UserBlock.objects.filter(blocker=user).values_list("blocked_id", flat=True),
    )
