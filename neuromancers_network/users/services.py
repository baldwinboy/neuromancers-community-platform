"""Account service helpers for identity and lifecycle changes."""

from __future__ import annotations

import logging

from django.utils import timezone

from neuromancers_network.core.audit import record_audit
from neuromancers_network.inbox.events import emit
from neuromancers_network.inbox.payloads import account_lifecycle_payload
from neuromancers_network.inbox.payloads import identity_change_payload

logger = logging.getLogger(__name__)


def _announce(  # noqa: PLR0913
    event_type: str,
    action: str,
    user,
    *,
    payload: dict,
    actor=None,
    request=None,
    reason: str = "",
) -> None:
    """Emit a bus event and write an audit row, both best-effort.

    The domain write that preceded this call is already committed, so a
    notification or audit failure must never roll it back or raise.
    """
    try:
        emit(
            event_type,
            payload=payload,
            event_ref=f"user.{user.pk}.{event_type}.{timezone.now().isoformat()}",
        )
    except Exception:
        logger.exception("Failed to emit %s for user %s", event_type, user.pk)
    try:
        record_audit(
            action=action,
            actor=actor,
            user=user,
            request=request,
            event_type=event_type,
            reason=reason,
        )
    except Exception:
        logger.exception("Failed to audit %s for user %s", action, user.pk)


def record_username_change(user, old_username: str) -> None:
    """Stamp the username cooldown, then announce and audit the change.

    Stamping is mandatory (it drives the cooldown); the notification and audit
    side effects are best-effort so they can never break the member's save.
    """
    user.username_changed_at = timezone.now()
    user.save(update_fields=["username_changed_at"])

    _announce(
        "username_changed",
        "account.username_change",
        user,
        payload=identity_change_payload(
            user,
            field="username",
            actor=user,
            recipients=[user],
        ),
        actor=user,
    )


def _unpublish_meetings(user) -> None:
    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingStatus  # noqa: PLC0415

    published = Meeting.objects.filter(peer=user, status=MeetingStatus.PUBLISHED)
    for meeting in published:
        meeting.unpublish()
        meeting.save(validate=False, update_fields=["status", "updated_at"])


def _cancel_bookings_for_peer(user) -> None:
    """Cancel the departing peer's active bookings and refund paid sessions."""
    from neuromancers_network.meetings.services import (  # noqa: PLC0415
        cancel_and_refund_for_peer,
    )

    try:
        cancel_and_refund_for_peer(user)
    except Exception:
        logger.exception("Failed to cancel bookings for user %s", user.pk)


def _set_calendar_token_active(user, *, active: bool) -> None:
    token = getattr(user, "calendar_feed_token", None)
    if token is not None and token.is_active != active:
        token.is_active = active
        token.save(update_fields=["is_active", "updated_at"])


def deactivate_account(user, *, actor=None, request=None, reason: str = "") -> None:
    """Deactivate *user*: block sign-in, withdraw content, revoke feeds.

    Idempotent. Meetings are unpublished (not deleted) so they can be
    republished after reactivation; the calendar feed token is deactivated.
    """
    if user is None or user.deactivated_at is not None:
        return

    user.is_active = False
    user.deactivated_at = timezone.now()
    user.deactivation_reason = (reason or "").strip()
    user.save(update_fields=["is_active", "deactivated_at", "deactivation_reason"])

    _unpublish_meetings(user)
    _cancel_bookings_for_peer(user)
    _set_calendar_token_active(user, active=False)

    _announce(
        "account_deactivated",
        "account.deactivate",
        user,
        payload=account_lifecycle_payload(
            user,
            actor=actor,
            recipients=[user],
            reason=user.deactivation_reason,
        ),
        actor=actor,
        request=request,
        reason=user.deactivation_reason,
    )


def reactivate_account(user, *, actor=None, request=None) -> None:
    """Reactivate *user*: restore sign-in and the calendar feed token.

    Meetings stay unpublished; the member republishes them deliberately.
    Idempotent.
    """
    if user is None or user.deactivated_at is None:
        return

    user.is_active = True
    user.deactivated_at = None
    user.deactivation_reason = ""
    user.save(update_fields=["is_active", "deactivated_at", "deactivation_reason"])

    _set_calendar_token_active(user, active=True)

    _announce(
        "account_reactivated",
        "account.reactivate",
        user,
        payload=account_lifecycle_payload(
            user,
            actor=actor,
            recipients=[user],
        ),
        actor=actor,
        request=request,
    )
