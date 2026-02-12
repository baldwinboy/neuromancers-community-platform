"""
Calendar export utilities for session sync with external calendar services.
Supports iCal (.ics) format and Google Calendar links.
"""

from datetime import datetime
from urllib.parse import urlencode

from django.http import HttpResponse
from django.utils import timezone


def generate_ics_event(
    uid: str,
    title: str,
    description: str,
    start: datetime,
    end: datetime,
    location: str = "",
    organizer: str = "",
) -> str:
    """Generate a single VEVENT in iCal format."""

    # Format datetime for iCal (UTC)
    def format_dt(dt):
        if timezone.is_aware(dt):
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{format_dt(timezone.now())}",
        f"DTSTART:{format_dt(start)}",
        f"DTEND:{format_dt(end)}",
        f"SUMMARY:{escape_ics_text(title)}",
    ]

    if description:
        lines.append(f"DESCRIPTION:{escape_ics_text(description)}")
    if location:
        lines.append(f"LOCATION:{escape_ics_text(location)}")
    if organizer:
        lines.append(
            f"ORGANIZER;CN={escape_ics_text(organizer)}:MAILTO:noreply@example.com"
        )

    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def escape_ics_text(text: str) -> str:
    """Escape special characters for iCal text fields."""
    if not text:
        return ""
    text = text.replace("\\", "\\\\")
    text = text.replace(",", "\\,")
    text = text.replace(";", "\\;")
    text = text.replace("\n", "\\n")
    return text


def generate_ics_calendar(events: list, calendar_name: str = "Sessions") -> str:
    """Generate a complete iCal calendar with multiple events."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//NEUROMANCERS//Sessions Calendar//EN",
        f"X-WR-CALNAME:{escape_ics_text(calendar_name)}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for event in events:
        lines.append(generate_ics_event(**event))

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def create_ics_response(events: list, filename: str = "sessions.ics") -> HttpResponse:
    """Create an HTTP response with an ICS file download."""
    ics_content = generate_ics_calendar(events)
    response = HttpResponse(ics_content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def get_google_calendar_url(
    title: str,
    start: datetime,
    end: datetime,
    description: str = "",
    location: str = "",
) -> str:
    """Generate a Google Calendar event creation URL."""

    # Format datetime for Google Calendar
    def format_dt(dt):
        if timezone.is_aware(dt):
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y%m%dT%H%M%SZ")

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{format_dt(start)}/{format_dt(end)}",
    }

    if description:
        params["details"] = description
    if location:
        params["location"] = location

    base_url = "https://calendar.google.com/calendar/render"
    return f"{base_url}?{urlencode(params)}"


def get_outlook_calendar_url(
    title: str,
    start: datetime,
    end: datetime,
    description: str = "",
    location: str = "",
) -> str:
    """Generate an Outlook Web calendar event creation URL."""

    def format_dt(dt):
        if timezone.is_aware(dt):
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "path": "/calendar/action/compose",
        "rru": "addevent",
        "subject": title,
        "startdt": format_dt(start),
        "enddt": format_dt(end),
    }

    if description:
        params["body"] = description
    if location:
        params["location"] = location

    base_url = "https://outlook.live.com/calendar/0/deeplink/compose"
    return f"{base_url}?{urlencode(params)}"


def get_yahoo_calendar_url(
    title: str,
    start: datetime,
    end: datetime,
    description: str = "",
    location: str = "",
) -> str:
    """Generate a Yahoo Calendar event creation URL."""

    def format_dt(dt):
        if timezone.is_aware(dt):
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y%m%dT%H%M%SZ")

    # Calculate duration in hours and minutes
    duration = end - start
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)

    params = {
        "v": "60",
        "title": title,
        "st": format_dt(start),
        "dur": f"{hours:02d}{minutes:02d}",
    }

    if description:
        params["desc"] = description
    if location:
        params["in_loc"] = location

    base_url = "https://calendar.yahoo.com/"
    return f"{base_url}?{urlencode(params)}"
