# ruff: noqa: PLC0415
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
# Sessions starting within this window receive a one-day reminder.
SESSION_REMINDER_DAY_HOURS = 24
# Sessions starting within this window receive a one-hour reminder.
SESSION_REMINDER_HOUR_HOURS = 1


def _existing_event_refs(event_types, refs):
    if not refs:
        return set()
    return set(
        NotificationEventLog.objects.filter(
            event_type__in=event_types,
            event_ref__in=refs,
        ).values_list("event_ref", flat=True),
    )


@shared_task
def emit_payment_reminders():
    """Emit ``payment_reminder_due`` for stale pending-payment bookings."""
    from neuromancers_network.meetings.models import MeetingRequest
    from neuromancers_network.meetings.models import MeetingRequestStatus

    now = timezone.now()
    threshold = now - timedelta(hours=PAYMENT_REMINDER_AFTER_HOURS)

    requests = list(
        MeetingRequest.objects.filter(
            status=MeetingRequestStatus.PENDING_PAYMENT,
            created_at__lte=threshold,
        ).select_related("support_seeker", "meeting", "meeting__peer"),
    )
    refs = [f"meetingrequest.{request.pk}.payment_reminder" for request in requests]
    existing = _existing_event_refs(["payment_reminder_due"], refs)

    for request, ref in zip(requests, refs, strict=True):
        if ref in existing:
            continue

        from .events import emit
        from .payloads import booking_payload

        emit(
            "payment_reminder_due",
            payload=booking_payload(
                request,
                actor=None,
                recipients=[request.support_seeker],
            ),
            event_ref=ref,
        )


def _emit_session_reminder(session, event_type, suffix, existing_refs):
    from .events import emit
    from .payloads import booking_payload

    ref = f"meetingrequest.{session.pk}.{suffix}"
    if ref in existing_refs:
        return

    emit(
        event_type,
        payload=booking_payload(
            session,
            actor=session.meeting.peer,
            recipients=[session.support_seeker],
        ),
        event_ref=ref,
    )


@shared_task
def emit_session_reminders():
    """Emit day-ahead and hour-ahead reminders for upcoming sessions.

    Works from the request's start time when set (1:1), otherwise from the
    meeting's scheduled start (group), and only for sessions the seeker may
    still attend (approved or paid).
    """
    from django.db.models import Q

    from neuromancers_network.meetings.models import MeetingRequest
    from neuromancers_network.meetings.models import MeetingRequestStatus

    now = timezone.now()
    day_horizon = now + timedelta(hours=SESSION_REMINDER_DAY_HOURS)
    hour_horizon = now + timedelta(hours=SESSION_REMINDER_HOUR_HOURS)

    sessions = list(
        MeetingRequest.objects.filter(
            Q(requested_start_time__gt=now, requested_start_time__lte=day_horizon)
            | Q(
                requested_start_time__isnull=True,
                meeting__scheduled_at__gt=now,
                meeting__scheduled_at__lte=day_horizon,
            ),
            status__in=[
                MeetingRequestStatus.APPROVED,
                MeetingRequestStatus.PAID,
            ],
        ).select_related("support_seeker", "meeting", "meeting__peer"),
    )

    planned = []
    for session in sessions:
        start = session.requested_start_time or session.meeting.scheduled_at
        if start is None:
            continue
        if start <= hour_horizon:
            planned.append((session, "session_reminder_1h", "reminder_1h"))
        else:
            planned.append((session, "session_reminder_1d", "reminder_1d"))

    refs = [
        f"meetingrequest.{session.pk}.{suffix}"
        for session, _event_type, suffix in planned
    ]
    existing = _existing_event_refs(
        ["session_reminder_1h", "session_reminder_1d"],
        refs,
    )
    for session, event_type, suffix in planned:
        _emit_session_reminder(session, event_type, suffix, existing)


@shared_task
def emit_upcoming_meetings():
    """Emit ``meeting_upcoming`` for published meetings starting soon.

    Group attendees are represented by bookings (often without a session
    request), so recipients are the union of request seekers and active booking
    seekers, plus the host.
    """
    from neuromancers_network.meetings.models import BookingStatus
    from neuromancers_network.meetings.models import Meeting
    from neuromancers_network.meetings.models import MeetingStatus

    now = timezone.now()
    horizon = now + timedelta(hours=UPCOMING_MEETING_WINDOW_HOURS)

    meetings = list(
        Meeting.objects.filter(
            status=MeetingStatus.PUBLISHED,
            scheduled_at__gt=now,
            scheduled_at__lte=horizon,
        ).select_related("peer"),
    )
    refs = [f"meeting.{meeting.pk}.upcoming" for meeting in meetings]
    existing = _existing_event_refs(["meeting_upcoming"], refs)

    for meeting, ref in zip(meetings, refs, strict=True):
        if ref in existing:
            continue

        requests = list(meeting.requests.select_related("support_seeker").all())
        bookings = list(
            meeting.bookings.filter(
                status__in=[BookingStatus.PENDING, BookingStatus.PAID],
            ).select_related("support_seeker"),
        )
        seeker_users = {request.support_seeker for request in requests}
        seeker_users.update(booking.support_seeker for booking in bookings)
        seekers = sorted(seeker_users, key=lambda user: user.pk)
        if not seekers:
            continue

        from .events import emit
        from .payloads import user_id

        recipients = [meeting.peer, *seekers]
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
                    "booked_seeker_user_ids": [user_id(user) for user in seekers],
                },
            },
            event_ref=ref,
        )
