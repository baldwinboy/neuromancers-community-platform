"""Read-only ICS calendar feed."""

from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus

import pytest
from django.utils import timezone

from neuromancers_network.core.models import CalendarFeedToken
from neuromancers_network.meetings.models import BookingStatus
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def make_booking(*, status=BookingStatus.PENDING):
    seeker = UserFactory()
    booking = create_booking(
        meeting=create_meeting(peer=make_peer()),
        seeker=seeker,
        sessions=[
            {
                "requested_start_time": timezone.now() + timedelta(hours=24),
                "requested_duration_minutes": 30,
            },
        ],
    )
    booking.status = status
    booking.save(update_fields=["status"])
    token = CalendarFeedToken.objects.create(user=seeker)
    return booking, token


class TestCalendarFeedView:
    def test_active_booking_is_included(self, client):
        booking, token = make_booking()

        response = client.get(f"/calendar/{token.token}.ics")

        text = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert "SUMMARY:Meeting" in text
        assert f"booking-{booking.pk}" in text

    def test_cancelled_booking_is_excluded(self, client):
        booking, token = make_booking(status=BookingStatus.CANCELLED)

        response = client.get(f"/calendar/{token.token}.ics")

        text = response.content.decode()
        assert f"booking-{booking.pk}" not in text

    def test_non_published_meeting_is_excluded(self, client):
        booking, token = make_booking()
        booking.meeting.status = MeetingStatus.ARCHIVED
        booking.meeting.save(validate=False)

        response = client.get(f"/calendar/{token.token}.ics")

        text = response.content.decode()
        assert f"booking-{booking.pk}" not in text
