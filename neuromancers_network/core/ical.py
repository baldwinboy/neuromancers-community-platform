"""iCalendar generation and add-to-calendar links."""

from __future__ import annotations

from datetime import timedelta

from icalendar import Calendar
from icalendar import Event

DEFAULT_DURATION_MINUTES = 60


def _session_window(booking):
    from neuromancers_network.meetings.models import MeetingRequestStatus  # noqa: PLC0415

    meeting = booking.meeting
    active = {MeetingRequestStatus.APPROVED, MeetingRequestStatus.PAID}
    for session in booking.sessions.all():
        if session.status not in active:
            continue
        start = session.requested_start_time or meeting.scheduled_at
        if start is None:
            continue
        duration = (
            session.requested_duration_minutes
            or meeting.duration_minutes
            or DEFAULT_DURATION_MINUTES
        )
        yield session, start, start + timedelta(minutes=duration)


def build_ics(bookings) -> bytes:
    """Build an ICS calendar for the given bookings (one event per session)."""
    calendar = Calendar()
    calendar.add("prodid", "-//NEUROMANCERS//Calendar//EN")
    calendar.add("version", "2.0")

    for booking in bookings:
        for session, start, end in _session_window(booking):
            event = Event()
            event.add("summary", booking.meeting.title)
            event.add("dtstart", start)
            event.add("dtend", end)
            event.add("uid", f"booking-{booking.pk}-session-{session.pk}")
            if booking.meeting.meeting_link:
                event.add("url", booking.meeting.meeting_link)
                event.add("location", booking.meeting.meeting_link)
            calendar.add_component(event)

    return calendar.to_ical()
