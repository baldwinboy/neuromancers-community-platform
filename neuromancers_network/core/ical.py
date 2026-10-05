"""iCalendar generation and add-to-calendar links."""

from __future__ import annotations

from datetime import UTC
from datetime import timedelta
from urllib.parse import urlencode

from icalendar import Calendar
from icalendar import Event

DEFAULT_DURATION_MINUTES = 60


def _session_window(booking):
    meeting = booking.meeting
    for session in booking.sessions.all():
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


def _fmt_google(dt) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def google_calendar_link(*, title, start, end, details="", location=""):
    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{_fmt_google(start)}/{_fmt_google(end)}",
        "details": details,
        "location": location,
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def outlook_calendar_link(*, title, start, end, details="", location=""):
    params = {
        "path": "/calendar/action/compose",
        "rru": "addevent",
        "subject": title,
        "startdt": start.isoformat(),
        "enddt": end.isoformat(),
        "body": details,
        "location": location,
    }
    return "https://outlook.live.com/calendar/0/deeplink/compose?" + urlencode(params)
