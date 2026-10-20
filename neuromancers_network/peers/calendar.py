"""Materialise :class:`CalendarEvent` rows from availability and meetings.

Events are kept in sync by signals (see ``peers.signals``) so a peer's
published calendar can be rendered by an admin-authored calendar block without
recomputing availability or bookings at request time.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from neuromancers_network.peers.models import AvailabilityOccurrence
from neuromancers_network.peers.models import CalendarEvent
from neuromancers_network.peers.models.choices import CalendarEventKind
from neuromancers_network.peers.services import window_occurrences

HORIZON_DAYS = 365


def remove_events(source_type: str, source_id) -> None:
    """Delete every calendar event derived from a source object."""
    if source_id is None:
        return
    CalendarEvent.objects.filter(
        source_type=source_type,
        source_id=source_id,
    ).delete()


def _create_event(  # noqa: PLR0913
    *,
    owner,
    start,
    end,
    kind,
    source_type,
    source_id,
    title="",
    is_public_detail=False,
    participant_ids=(),
):
    return CalendarEvent.objects.create(
        owner=owner,
        start=start,
        end=end,
        kind=kind,
        title=title,
        is_public_detail=is_public_detail,
        participant_ids=list(participant_ids),
        source_type=source_type,
        source_id=source_id,
    )


def sync_availability(window) -> None:
    """(Re)build the available events for one availability window."""
    remove_events("availability", window.pk)
    if not window.start or not window.end:
        return
    now = timezone.now()
    horizon = now + timedelta(days=HORIZON_DAYS)
    if window.occurrence == AvailabilityOccurrence.NONE:
        occurrences = [(window.start, window.end)]
    else:
        occurrences = list(window_occurrences(window, now, horizon))
    for start, end in occurrences:
        if end <= now:
            continue
        _create_event(
            owner=window.peer,
            start=start,
            end=end,
            kind=CalendarEventKind.AVAILABLE,
            source_type="availability",
            source_id=window.pk,
        )


def sync_request(request) -> None:
    """(Re)build the calendar event for an approved or paid 1:1 request."""
    from neuromancers_network.meetings.models import MeetingRequestStatus  # noqa: PLC0415

    remove_events("request", request.pk)
    if request.status not in {
        MeetingRequestStatus.APPROVED,
        MeetingRequestStatus.PAID,
    }:
        return
    meeting = request.meeting
    start = request.requested_start_time
    duration = request.requested_duration_minutes
    if start is None or not duration:
        return
    _create_event(
        owner=meeting.peer,
        start=start,
        end=start + timedelta(minutes=duration),
        kind=CalendarEventKind.ONE_TO_ONE,
        source_type="request",
        source_id=request.pk,
        title=meeting.title,
        participant_ids=[request.support_seeker_id],
    )


def sync_meeting(meeting) -> None:
    """(Re)build the calendar event for a published group meeting."""
    from neuromancers_network.meetings.models import MeetingStatus  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingType  # noqa: PLC0415

    remove_events("meeting", meeting.pk)
    if (
        meeting.meeting_type != MeetingType.GROUP
        or meeting.status != MeetingStatus.PUBLISHED
    ):
        return
    if meeting.scheduled_at is None or not meeting.duration_minutes:
        return
    _create_event(
        owner=meeting.peer,
        start=meeting.scheduled_at,
        end=meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes),
        kind=CalendarEventKind.GROUP,
        source_type="meeting",
        source_id=meeting.pk,
        title=meeting.title,
        is_public_detail=True,
    )
