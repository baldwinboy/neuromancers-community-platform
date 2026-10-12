from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.models import CalendarEvent
from neuromancers_network.peers.tests.factories import make_availability
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.tests.factories import UserFactory

ACCESS_NEEDS = "Wheelchair access"
SESSION_ACCESS_NEEDS = "Quiet room"
SESSION_DURATION = 30
LONGER_SESSION_DURATION = 60
FIRST_SESSION_OFFSET_HOURS = 24
SECOND_SESSION_OFFSET_HOURS = 48
EXPECTED_SINGLE_SESSION = 1
EXPECTED_SESSION_COUNT = 2
TERMS = "Be kind and respectful"
PROFILE_ACCESS_NEEDS = "Step-free access"
OVERRIDE_ACCESS_NEEDS = "Quiet room"

pytestmark = pytest.mark.django_db


def make_booking(**kwargs):
    meeting = create_meeting(peer=make_peer())
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
        assert booking.currency == meeting.currency
        assert booking.access_needs == ACCESS_NEEDS

    def test_ineligible_peer_cannot_be_booked(self):
        meeting = create_meeting(peer=make_peer(is_approved=False))

        with pytest.raises(ValidationError, match="not currently available"):
            create_booking(meeting=meeting, seeker=UserFactory())

    def test_creates_sessions(self):
        booking = create_booking(
            meeting=create_meeting(peer=make_peer()),
            seeker=UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        assert booking.sessions.count() == EXPECTED_SINGLE_SESSION
        assert booking.sessions.first().requested_duration_minutes == SESSION_DURATION

    def test_access_needs_inherited_by_sessions(self):
        booking = create_booking(
            meeting=create_meeting(peer=make_peer()),
            seeker=UserFactory(),
            access_needs=SESSION_ACCESS_NEEDS,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        assert booking.sessions.first().access_needs == SESSION_ACCESS_NEEDS


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
        meeting = create_meeting(peer=make_peer())
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


def _future_window(peer):
    """Create a 09:00-11:00 availability window two days out; return its start."""
    start = (timezone.now() + timedelta(days=2)).replace(
        hour=9,
        minute=0,
        second=0,
        microsecond=0,
    )
    make_availability(peer, start=start, end=start + timedelta(hours=2))
    return start


class TestBookingAvailability:
    def test_slot_within_window_is_allowed(self):
        peer = make_peer()
        start = _future_window(peer)

        booking = create_booking(
            meeting=create_meeting(peer=peer),
            seeker=UserFactory(),
            sessions=[
                {
                    "requested_start_time": start,
                    "requested_duration_minutes": SESSION_DURATION,
                },
            ],
        )

        assert booking.sessions.first().requested_start_time == start

    def test_slot_outside_window_is_rejected(self):
        peer = make_peer()
        start = _future_window(peer)

        with pytest.raises(ValidationError):
            create_booking(
                meeting=create_meeting(peer=peer),
                seeker=UserFactory(),
                sessions=[
                    {
                        "requested_start_time": start + timedelta(hours=5),
                        "requested_duration_minutes": SESSION_DURATION,
                    },
                ],
            )

    def test_slot_ending_past_window_is_rejected(self):
        peer = make_peer()
        start = _future_window(peer)

        with pytest.raises(ValidationError):
            create_booking(
                meeting=create_meeting(peer=peer),
                seeker=UserFactory(),
                sessions=[
                    {
                        "requested_start_time": start + timedelta(hours=1, minutes=45),
                        "requested_duration_minutes": SESSION_DURATION,
                    },
                ],
            )

    def test_peer_without_windows_is_unrestricted(self):
        start = timezone.now() + timedelta(days=2)

        booking = create_booking(
            meeting=create_meeting(peer=make_peer()),
            seeker=UserFactory(),
            sessions=[
                {
                    "requested_start_time": start,
                    "requested_duration_minutes": SESSION_DURATION,
                },
            ],
        )

        assert booking.sessions.get().requested_start_time == start

    def test_booking_creates_private_calendar_event(self):
        peer = make_peer()
        start = _future_window(peer)
        seeker = UserFactory()

        booking = create_booking(
            meeting=create_meeting(peer=peer),
            seeker=seeker,
            sessions=[
                {
                    "requested_start_time": start,
                    "requested_duration_minutes": SESSION_DURATION,
                },
            ],
        )

        event = CalendarEvent.objects.get(
            source_type="request",
            source_id=booking.sessions.first().pk,
        )
        assert event.kind == "one_to_one"
        assert event.owner_id == peer.pk
        assert event.participant_ids == [seeker.pk]

    def test_group_meeting_ignores_windows(self):
        peer = make_peer()
        _future_window(peer)
        meeting = Meeting.objects.create(
            peer=peer,
            title="Group",
            description="Test",
            meeting_type=MeetingType.GROUP,
            pricing_type=PricingType.FIXED,
            price=5,
            approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
            currency="GBP",
            scheduled_at=timezone.now() + timedelta(days=3),
            duration_minutes=60,
        )
        outside_window = timezone.now() + timedelta(days=2)

        booking = create_booking(
            meeting=meeting,
            seeker=UserFactory(),
            sessions=[
                {
                    "requested_start_time": outside_window,
                    "requested_duration_minutes": SESSION_DURATION,
                },
            ],
        )

        assert booking.sessions.get().requested_start_time == outside_window


class TestBookingRequestStatus:
    def test_pay_after_join_is_approved(self):
        booking = create_booking(
            meeting=create_meeting(peer=make_peer()),
            seeker=UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        assert booking.sessions.first().status == MeetingRequestStatus.APPROVED

    def test_pay_before_join_awaits_payment(self):
        meeting = create_meeting(peer=make_peer())
        meeting.approval_policy = ApprovalPolicy.PAY_BEFORE_JOIN
        meeting.save()

        booking = create_booking(
            meeting=meeting,
            seeker=UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        assert booking.sessions.first().status == MeetingRequestStatus.PENDING_PAYMENT

    def test_approval_required_awaits_approval(self):
        meeting = create_meeting(peer=make_peer())
        meeting.approval_policy = ApprovalPolicy.APPROVAL_REQUIRED
        meeting.save()

        booking = create_booking(
            meeting=meeting,
            seeker=UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        assert booking.sessions.first().status == MeetingRequestStatus.PENDING_APPROVAL


def make_policy_meeting(*, approval_policy):
    return Meeting(
        peer=UserFactory(),
        title="Test meeting",
        description="Test",
        meeting_type=MeetingType.ONE_ON_ONE,
        pricing_type=PricingType.FIXED,
        approval_policy=approval_policy,
        currency="GBP",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )


def make_policy_request(*, approval_policy):
    meeting = make_policy_meeting(approval_policy=approval_policy)
    request = MeetingRequest(meeting=meeting, support_seeker=UserFactory())
    request.start()
    return request


class TestApprovalPolicy:
    def test_approval_required_starts_pending_approval(self):
        request = make_policy_request(approval_policy=ApprovalPolicy.APPROVAL_REQUIRED)
        assert request.status == MeetingRequestStatus.PENDING_APPROVAL
        assert request.requires_approval is True
        assert request.requires_payment_before_join is False
        assert request.can_join is False
        assert request.can_pay is False

    def test_approval_required_then_paid_before_join(self):
        request = make_policy_request(approval_policy=ApprovalPolicy.APPROVAL_REQUIRED)
        request.approve()
        assert request.status == MeetingRequestStatus.APPROVED
        assert request.can_join is True
        assert request.can_pay is True
        request.mark_paid()
        assert request.status == MeetingRequestStatus.PAID
        assert request.can_join is True

    def test_pay_before_join_starts_pending_payment(self):
        request = make_policy_request(approval_policy=ApprovalPolicy.PAY_BEFORE_JOIN)
        assert request.status == MeetingRequestStatus.PENDING_PAYMENT
        assert request.requires_approval is False
        assert request.requires_payment_before_join is True
        assert request.can_join is False
        assert request.can_pay is True

    def test_pay_before_join_can_only_join_after_paid(self):
        request = make_policy_request(approval_policy=ApprovalPolicy.PAY_BEFORE_JOIN)
        request.mark_paid()
        assert request.status == MeetingRequestStatus.PAID
        assert request.can_join is True

    def test_pay_after_join_starts_approved(self):
        request = make_policy_request(approval_policy=ApprovalPolicy.PAY_AFTER_JOIN)
        assert request.status == MeetingRequestStatus.APPROVED
        assert request.requires_approval is False
        assert request.requires_payment_before_join is False
        assert request.allows_join_before_payment is True
        assert request.can_join is True
        assert request.can_pay is True

    def test_pay_after_join_can_pay_later(self):
        request = make_policy_request(approval_policy=ApprovalPolicy.PAY_AFTER_JOIN)
        request.mark_paid()
        assert request.status == MeetingRequestStatus.PAID

    def test_one_on_one_request_must_start_at_least_10_minutes_after_meeting_creation(
        self,
    ):
        meeting = make_policy_meeting(approval_policy=ApprovalPolicy.APPROVAL_REQUIRED)
        meeting.save()
        request = MeetingRequest(
            meeting=meeting,
            support_seeker=UserFactory(),
            requested_start_time=meeting.created_at + timedelta(minutes=5),
        )

        with pytest.raises(ValidationError):
            request.full_clean()


def make_meeting_with_terms(terms=TERMS):
    meeting = create_meeting(peer=make_peer())
    meeting.terms = terms
    meeting.save()
    return meeting


class TestTermsAgreement:
    def test_terms_required_to_book(self):
        meeting = make_meeting_with_terms()

        with pytest.raises(ValidationError):
            create_booking(meeting=meeting, seeker=UserFactory())

    def test_agreed_terms_are_snapshotted_on_sessions(self):
        meeting = make_meeting_with_terms()
        seeker = UserFactory()

        booking = create_booking(
            meeting=meeting,
            seeker=seeker,
            peer_terms=TERMS,
            terms_accepted=True,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        session = booking.sessions.first()
        assert session.terms_accepted is True
        assert session.peer_terms == TERMS
        assert session.terms_accepted_at is not None

    def test_meeting_without_terms_needs_no_acceptance(self):
        meeting = create_meeting(peer=make_peer())

        booking = create_booking(meeting=meeting, seeker=UserFactory())

        assert booking.pk is not None


class TestAccessNeeds:
    def test_defaults_to_profile(self):
        seeker = UserFactory()
        UserProfile.objects.create(user=seeker, access_needs=PROFILE_ACCESS_NEEDS)

        booking = create_booking(
            meeting=create_meeting(peer=make_peer()),
            seeker=seeker,
        )

        assert booking.access_needs == PROFILE_ACCESS_NEEDS

    def test_per_request_override_wins(self):
        seeker = UserFactory()
        UserProfile.objects.create(user=seeker, access_needs=PROFILE_ACCESS_NEEDS)

        booking = create_booking(
            meeting=create_meeting(peer=make_peer()),
            seeker=seeker,
            access_needs=OVERRIDE_ACCESS_NEEDS,
        )

        assert booking.access_needs == OVERRIDE_ACCESS_NEEDS
