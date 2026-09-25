import pytest
from django.core.exceptions import ValidationError

from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.tests.factories import UserFactory

SESSION_DURATION = 30
TERMS = "Be kind and respectful"
PROFILE_ACCESS_NEEDS = "Step-free access"
OVERRIDE_ACCESS_NEEDS = "Quiet room"

pytestmark = pytest.mark.django_db


def make_meeting_with_terms(terms=TERMS):
    meeting = create_meeting(peer=UserFactory())
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
        meeting = create_meeting(peer=UserFactory())

        booking = create_booking(meeting=meeting, seeker=UserFactory())

        assert booking.pk is not None


class TestAccessNeeds:
    def test_defaults_to_profile(self):
        seeker = UserFactory()
        UserProfile.objects.create(user=seeker, access_needs=PROFILE_ACCESS_NEEDS)

        booking = create_booking(
            meeting=create_meeting(peer=UserFactory()),
            seeker=seeker,
        )

        assert booking.access_needs == PROFILE_ACCESS_NEEDS

    def test_per_request_override_wins(self):
        seeker = UserFactory()
        UserProfile.objects.create(user=seeker, access_needs=PROFILE_ACCESS_NEEDS)

        booking = create_booking(
            meeting=create_meeting(peer=UserFactory()),
            seeker=seeker,
            access_needs=OVERRIDE_ACCESS_NEEDS,
        )

        assert booking.access_needs == OVERRIDE_ACCESS_NEEDS

    def test_sessions_inherit_booking_access_needs(self):
        seeker = UserFactory()

        booking = create_booking(
            meeting=create_meeting(peer=UserFactory()),
            seeker=seeker,
            access_needs=OVERRIDE_ACCESS_NEEDS,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        assert booking.sessions.first().access_needs == OVERRIDE_ACCESS_NEEDS
