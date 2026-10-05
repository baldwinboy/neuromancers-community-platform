from datetime import timedelta

import pytest
from django.utils import timezone

from neuromancers_network.core.ical import build_ics
from neuromancers_network.core.ical import google_calendar_link
from neuromancers_network.core.ical import outlook_calendar_link
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.users.tests.factories import UserFactory

SESSION_DURATION = 30

pytestmark = pytest.mark.django_db


def make_booking_with_session():
    return create_booking(
        meeting=create_meeting(peer=UserFactory()),
        seeker=UserFactory(),
        sessions=[
            {
                "requested_start_time": timezone.now() + timedelta(hours=24),
                "requested_duration_minutes": SESSION_DURATION,
            },
        ],
    )


class TestBuildIcs:
    def test_contains_calendar_and_event(self):
        booking = make_booking_with_session()

        text = build_ics([booking]).decode()

        assert "BEGIN:VCALENDAR" in text
        assert "BEGIN:VEVENT" in text
        assert "SUMMARY:Meeting" in text
        assert f"booking-{booking.pk}-session-{booking.sessions.first().pk}" in text


class TestExternalLinks:
    def test_google_link(self):
        start = timezone.now()
        end = start + timedelta(hours=1)

        url = google_calendar_link(title="Session", start=start, end=end)

        assert url.startswith("https://calendar.google.com/calendar/render?")
        assert "action=TEMPLATE" in url

    def test_outlook_link(self):
        start = timezone.now()
        end = start + timedelta(hours=1)

        url = outlook_calendar_link(title="Session", start=start, end=end)

        assert url.startswith("https://outlook.live.com/calendar/0/deeplink/compose?")
        assert "rru=addevent" in url
