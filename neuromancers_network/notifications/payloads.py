"""Normalized event-payload builders.

Kept separate from the signal receivers so scheduled tasks and (future) call
sites can build the same stable payload shape without importing receiver code.
"""

from __future__ import annotations


def user_id(user) -> int | None:
    return user.pk if user is not None else None


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
            "is_published": review.is_published,
            "peer_user_id": user_id(review.peer),
            "reviewer_user_id": user_id(review.reviewer),
        },
    }
