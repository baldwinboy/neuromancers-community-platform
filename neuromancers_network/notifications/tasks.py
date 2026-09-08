"""Scheduled bus emissions for time-based events.

Unlike signal-driven events (which fire once per state change), these tasks
scan for *conditions* and could otherwise re-emit on every beat run. Each task
therefore checks the store for an existing log row with the same ``event_ref``
and skips objects already recorded.
"""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models.event_log import NotificationEventLog

# Payments in PENDING_PAYMENT older than this are considered due a reminder.
PAYMENT_REMINDER_AFTER_HOURS = 24
# Meetings starting within this window (and in the future) are "upcoming".
UPCOMING_MEETING_WINDOW_HOURS = 24


@shared_task
def emit_payment_reminders():
    """Emit ``payment_reminder_due`` for stale pending-payment bookings."""
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    now = timezone.now()
    threshold = now - timedelta(hours=PAYMENT_REMINDER_AFTER_HOURS)

    requests = MeetingRequest.objects.filter(
        status="pending_payment",
        created_at__lte=threshold,
    ).select_related("support_seeker", "meeting", "meeting__peer")

    for request in requests:
        ref = f"meetingrequest.{request.pk}.payment_reminder"
        if NotificationEventLog.objects.filter(
            event_type="payment_reminder_due",
            event_ref=ref,
        ).exists():
            continue

        from .events import emit  # noqa: PLC0415
        from .payloads import booking_payload  # noqa: PLC0415

        emit(
            "payment_reminder_due",
            payload=booking_payload(
                request,
                actor=None,
                recipients=[request.support_seeker],
            ),
            event_ref=ref,
        )


@shared_task
def emit_upcoming_meetings():
    """Emit ``meeting_upcoming`` for published meetings starting soon."""
    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingStatus  # noqa: PLC0415

    now = timezone.now()
    horizon = now + timedelta(hours=UPCOMING_MEETING_WINDOW_HOURS)

    meetings = Meeting.objects.filter(
        status=MeetingStatus.PUBLISHED,
        scheduled_at__gt=now,
        scheduled_at__lte=horizon,
    ).select_related("peer")

    for meeting in meetings:
        ref = f"meeting.{meeting.pk}.upcoming"
        if NotificationEventLog.objects.filter(
            event_type="meeting_upcoming",
            event_ref=ref,
        ).exists():
            continue

        requests = list(meeting.requests.select_related("support_seeker").all())
        recipients = [meeting.peer]
        recipients += [req.support_seeker for req in requests]
        if not requests:
            continue

        from .events import emit  # noqa: PLC0415
        from .payloads import user_id  # noqa: PLC0415

        emit(
            "meeting_upcoming",
            payload={
                "actor_user_id": user_id(meeting.peer),
                "recipient_user_ids": [
                    user_id(user) for user in recipients if user is not None
                ],
                "object_type": "meeting",
                "object_id": meeting.pk,
                "meta": {
                    "meeting_id": meeting.pk,
                    "meeting_title": meeting.title,
                    "peer_user_id": user_id(meeting.peer),
                    "scheduled_at": (
                        meeting.scheduled_at.isoformat()
                        if meeting.scheduled_at
                        else None
                    ),
                    "booked_seeker_user_ids": [
                        user_id(req.support_seeker) for req in requests
                    ],
                },
            },
            event_ref=ref,
        )
