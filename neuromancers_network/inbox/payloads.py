"""Normalized event-payload builders.

Kept separate from the signal receivers so scheduled tasks and (future) call
sites can build the same stable payload shape without importing receiver code.
"""

from __future__ import annotations


def user_id(user) -> int | None:
    return user.pk if user is not None else None


def _account_reference(user) -> dict:
    return {
        "user_id": user_id(user),
        "username": getattr(user, "username", "") or "",
        "name": getattr(user, "name", "") or "",
    }


def account_lifecycle_payload(  # noqa: PLR0913
    user,
    *,
    actor=None,
    recipients=(),
    reason: str = "",
    deletion_scheduled_for=None,
    deletion_cancel_url: str = "",
):
    """Payload for account deactivation/reactivation/deletion events."""
    meta = _account_reference(user)
    if reason:
        meta["reason"] = reason
    if deletion_scheduled_for is not None:
        meta["deletion_scheduled_for"] = deletion_scheduled_for.isoformat()
    if deletion_cancel_url:
        meta["deletion_cancel_url"] = deletion_cancel_url
    return {
        "actor_user_id": user_id(actor),
        "recipient_user_ids": [user_id(u) for u in recipients if u is not None],
        "object_type": "user",
        "object_id": user_id(user),
        "meta": meta,
    }


def identity_change_payload(user, *, field: str, actor=None, recipients=()):
    """Payload for email/username change events (no raw values retained)."""
    meta = _account_reference(user)
    meta["field"] = field
    return {
        "actor_user_id": user_id(actor),
        "recipient_user_ids": [user_id(u) for u in recipients if u is not None],
        "object_type": "user",
        "object_id": user_id(user),
        "meta": meta,
    }


def meeting_lifecycle_payload(meeting, *, actor=None, recipients=(), status: str = ""):
    """Payload for a single meeting's unpublish/delete event."""
    return {
        "actor_user_id": user_id(actor),
        "recipient_user_ids": [user_id(u) for u in recipients if u is not None],
        "object_type": "meeting",
        "object_id": meeting.pk,
        "meta": {
            "meeting_id": meeting.pk,
            "meeting_title": meeting.title,
            "peer_user_id": user_id(meeting.peer),
            "status": status,
        },
    }


def meetings_bulk_payload(
    *,
    actor=None,
    recipients=(),
    meeting_ids=(),
    peer_user_id=None,
    title: str = "",
):
    """Payload for bulk meeting unpublish/delete events."""
    ids = [int(pk) for pk in meeting_ids]
    return {
        "actor_user_id": user_id(actor),
        "recipient_user_ids": [user_id(u) for u in recipients if u is not None],
        "object_type": "meeting",
        "object_id": None,
        "meta": {
            "meeting_ids": ids,
            "count": len(ids),
            "peer_user_id": peer_user_id,
            "meeting_title": title,
        },
    }


def ban_payload(  # noqa: PLR0913
    *,
    target: str,
    target_type: str,
    actor=None,
    recipients=(),
    reason: str = "",
    expires_at=None,
):
    """Payload for IP/email moderation ban events.

    *target* is the banned IP or email address; *target_type* is ``"ip"`` or
    ``"email"``. Raw values are included because these events are only visible
    to moderators and the affected party.
    """
    meta = {"target": target, "target_type": target_type}
    if reason:
        meta["reason"] = reason
    if expires_at is not None:
        meta["expires_at"] = expires_at.isoformat()
    return {
        "actor_user_id": user_id(actor),
        "recipient_user_ids": [user_id(u) for u in recipients if u is not None],
        "object_type": "moderation",
        "object_id": None,
        "meta": meta,
    }


def booking_payload(request, *, actor=None, recipients=()):
    meeting = request.meeting
    return {
        "actor_user_id": user_id(actor),
        "recipient_user_ids": [user_id(u) for u in recipients if u is not None],
        "object_type": "meetingrequest",
        "object_id": request.pk,
        "meta": {
            "meeting_request_id": request.pk,
            "meeting_id": meeting.pk,
            "meeting_title": meeting.title,
            "status": request.status,
            "peer_user_id": user_id(meeting.peer),
            "support_seeker_user_id": user_id(request.support_seeker),
            "scheduled_at": (
                request.requested_start_time.isoformat()
                if request.requested_start_time
                else None
            ),
        },
    }


def calendar_ics_url(user) -> str:
    """Return the user's read-only calendar feed URL, or an empty string."""
    token = getattr(user, "calendar_feed_token", None)
    if token is None or not token.is_active:
        return ""
    return f"/calendar/{token.token}.ics"


def session_payload(booking, *, actor=None, recipients=()):
    """Payload for booking/session confirmation and reminder emails."""
    meeting = booking.meeting
    sessions = list(booking.sessions.all())
    first = sessions[0] if sessions else None
    return {
        "actor_user_id": user_id(actor),
        "recipient_user_ids": [user_id(u) for u in recipients if u is not None],
        "object_type": "booking",
        "object_id": booking.pk,
        "meta": {
            "booking_id": booking.pk,
            "meeting_id": meeting.pk,
            "meeting_title": meeting.title,
            "meeting_link": (
                (first.meeting_link if first else "") or meeting.meeting_link
            ),
            "price": (
                str(booking.total_amount) if booking.total_amount is not None else None
            ),
            "currency": booking.currency,
            "access_needs": booking.access_needs,
            "peer_terms": (first.peer_terms if first else "") or meeting.terms,
            "terms_accepted_at": (
                first.terms_accepted_at.isoformat()
                if first is not None and first.terms_accepted_at
                else None
            ),
            "sessions": [
                {
                    "id": session.pk,
                    "requested_start_time": (
                        session.requested_start_time.isoformat()
                        if session.requested_start_time
                        else None
                    ),
                    "requested_duration_minutes": session.requested_duration_minutes,
                }
                for session in sessions
            ],
            "ics_url": calendar_ics_url(booking.support_seeker),
        },
    }


def refund_payload(refund_request, *, actor=None, recipients=()):
    request = refund_request.meeting_request
    return {
        "actor_user_id": user_id(actor),
        "recipient_user_ids": [user_id(u) for u in recipients if u is not None],
        "object_type": "refundrequest",
        "object_id": refund_request.pk,
        "meta": {
            "refund_request_id": refund_request.pk,
            "meeting_request_id": request.pk,
            "meeting_id": request.meeting_id,
            "meeting_title": request.meeting.title,
            "status": refund_request.status,
            "reason": refund_request.reason,
            "peer_user_id": user_id(request.meeting.peer),
            "support_seeker_user_id": user_id(request.support_seeker),
        },
    }


def review_payload(review, *, actor=None, recipients=()):
    return {
        "actor_user_id": user_id(actor),
        "recipient_user_ids": [user_id(u) for u in recipients if u is not None],
        "object_type": "review",
        "object_id": review.pk,
        "meta": {
            "review_id": review.pk,
            "meeting_request_id": review.meeting_request_id,
            "meeting_id": review.meeting_request.meeting_id,
            "meeting_title": review.meeting_request.meeting.title,
            "rating": review.rating,
            "status": review.status,
            "peer_user_id": user_id(review.peer),
            "reviewer_user_id": user_id(review.reviewer),
        },
    }
