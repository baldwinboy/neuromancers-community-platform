"""Account service helpers for identity changes."""

from __future__ import annotations

import logging

from django.utils import timezone

from neuromancers_network.core.audit import record_audit
from neuromancers_network.inbox.events import emit
from neuromancers_network.inbox.payloads import identity_change_payload

logger = logging.getLogger(__name__)


def record_username_change(user, old_username: str) -> None:
    """Stamp the username cooldown, then announce and audit the change.

    Stamping is mandatory (it drives the cooldown); the notification and audit
    side effects are best-effort so they can never break the member's save.
    """
    user.username_changed_at = timezone.now()
    user.save(update_fields=["username_changed_at"])

    try:
        emit(
            "username_changed",
            payload=identity_change_payload(
                user,
                field="username",
                actor=user,
                recipients=[user],
            ),
            event_ref=(
                f"user.{user.pk}.username_changed.{user.username_changed_at.isoformat()}"
            ),
        )
    except Exception:
        logger.exception("Failed to emit username_changed for user %s", user.pk)

    try:
        record_audit(
            action="account.username_change",
            actor=user,
            user=user,
            changes={"username": [old_username, user.username]},
        )
    except Exception:
        logger.exception("Failed to audit username change for user %s", user.pk)
