from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_fsm import TransitionNotAllowed

from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import BookingStatus
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.users.tests.factories import UserFactory

ACCESS_NEEDS = "Wheelchair access"
SESSION_ACCESS_NEEDS = "Quiet room"
SESSION_DURATION = 30
LONGER_SESSION_DURATION = 60
FIRST_SESSION_OFFSET_HOURS = 24
SECOND_SESSION_OFFSET_HOURS = 48
EXPECTED_SINGLE_SESSION = 1
EXPECTED_SESSION_COUNT = 2

pytestmark = pytest.mark.django_db


def make_booking(**kwargs):
    meeting = create_meeting(peer=UserFactory())
    seeker = UserFactory()
    booking = create_booking(meeting=meeting, seeker=seeker, **kwargs)
    return booking, meeting, seeker


def make_session(booking, *, offset_hours):
    return MeetingRequest.objects.create(
        meeting=booking.meeting,
        support_seeker=booking.support_seeker,
        booking=booking,
        requested_start_time=timezone.now() + timedelta(hours=offset_hours),
        requested_duration_minutes=SESSION_DURATION,
    )


class TestCreateBooking:
    def test_creates_booking_with_defaults(self):
        booking, meeting, seeker = make_booking(access_needs=ACCESS_NEEDS)

        assert booking.meeting == meeting
        assert booking.support_seeker == seeker
        assert booking.status == BookingStatus.PENDING
        assert booking.currency == meeting.currency
        assert booking.access_needs == ACCESS_NEEDS

    def test_creates_sessions(self):
        booking = create_booking(
            meeting=create_meeting(peer=UserFactory()),
            seeker=UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        assert booking.sessions.count() == EXPECTED_SINGLE_SESSION
        assert booking.sessions.first().requested_duration_minutes == SESSION_DURATION

    def test_access_needs_inherited_by_sessions(self):
        booking = create_booking(
            meeting=create_meeting(peer=UserFactory()),
            seeker=UserFactory(),
            access_needs=SESSION_ACCESS_NEEDS,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        assert booking.sessions.first().access_needs == SESSION_ACCESS_NEEDS

    def test_explicit_status_is_kept(self):
        booking, _meeting, _seeker = make_booking(status=BookingStatus.PAID)

        assert booking.status == BookingStatus.PAID


class TestBookingStatus:
    def test_mark_paid(self):
        booking, _meeting, _seeker = make_booking()

        booking.mark_paid()
        booking.save()

        booking.refresh_from_db()
        assert booking.status == BookingStatus.PAID

    def test_cancel_from_pending(self):
        booking, _meeting, _seeker = make_booking()

        booking.cancel()
        booking.save()

        booking.refresh_from_db()
        assert booking.status == BookingStatus.CANCELLED

    def test_refund_requires_paid(self):
        booking, _meeting, _seeker = make_booking()

        with pytest.raises(TransitionNotAllowed):
            booking.refund()

    def test_refund_from_paid(self):
        booking, _meeting, _seeker = make_booking(status=BookingStatus.PAID)

        booking.refund()
        booking.save()

        booking.refresh_from_db()
        assert booking.status == BookingStatus.REFUNDED


class TestSessionConstraints:
    def test_distinct_times_allowed(self):
        booking, _meeting, _seeker = make_booking()

        make_session(booking, offset_hours=FIRST_SESSION_OFFSET_HOURS)
        make_session(booking, offset_hours=SECOND_SESSION_OFFSET_HOURS)

        assert booking.sessions.count() == EXPECTED_SESSION_COUNT

    def test_duplicate_booking_and_time_rejected(self):
        booking, _meeting, _seeker = make_booking()
        when = timezone.now() + timedelta(hours=FIRST_SESSION_OFFSET_HOURS)
        MeetingRequest.objects.create(
            meeting=booking.meeting,
            support_seeker=booking.support_seeker,
            booking=booking,
            requested_start_time=when,
            requested_duration_minutes=SESSION_DURATION,
        )

        with pytest.raises(ValidationError):
            MeetingRequest.objects.create(
                meeting=booking.meeting,
                support_seeker=booking.support_seeker,
                booking=booking,
                requested_start_time=when,
                requested_duration_minutes=SESSION_DURATION,
            )

    def test_same_seeker_can_book_same_meeting_twice(self):
        meeting = create_meeting(peer=UserFactory())
        seeker = UserFactory()

        first = create_booking(
            meeting=meeting,
            seeker=seeker,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )
        second = create_booking(
            meeting=meeting,
            seeker=seeker,
            sessions=[{"requested_duration_minutes": LONGER_SESSION_DURATION}],
        )

        assert first.pk != second.pk
        assert (
            Booking.objects.filter(
                meeting=meeting,
                support_seeker=seeker,
            ).count()
            == EXPECTED_SESSION_COUNT
        )
        assert (
            MeetingRequest.objects.filter(
                meeting=meeting,
                support_seeker=seeker,
            ).count()
            == EXPECTED_SESSION_COUNT
        )
