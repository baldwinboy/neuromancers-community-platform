from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone

from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.models import CalendarEvent
from neuromancers_network.peers.models.settings import PeerRequirementsSettings
from neuromancers_network.peers.selectors import peer_calendar_events
from neuromancers_network.peers.services import available_slots
from neuromancers_network.peers.services import eligibility_failures
from neuromancers_network.peers.services import eligible_peer_q
from neuromancers_network.peers.services import is_eligible_peer
from neuromancers_network.peers.tests.factories import make_availability
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.models import User
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

EXPECTED_DAILY_SLOTS = 3


class TestEligibility:
    def test_unknown_user_is_not_eligible(self):
        assert is_eligible_peer(None) is False

    def test_user_without_peer_profile(self, user):
        assert is_eligible_peer(user) is False
        assert "not_approved" in eligibility_failures(user)

    def test_full_peer_is_eligible(self):
        assert is_eligible_peer(make_peer()) is True

    def test_eligible_peer_q_matches_only_eligible_users(self):
        eligible = make_peer()
        make_peer(is_approved=False)

        assert list(User.objects.filter(eligible_peer_q())) == [eligible]

    def test_unapproved_peer_is_not_eligible(self):
        assert is_eligible_peer(make_peer(is_approved=False)) is False

    def test_missing_subscription(self):
        user = make_peer(subscription_status=None)
        assert "no_active_subscription" in eligibility_failures(user)
        assert is_eligible_peer(user) is False

    def test_incomplete_kyc(self):
        user = make_peer(kyc_completed=False)
        assert "kyc_incomplete" in eligibility_failures(user)

    def test_verification_requirement_toggle(self):
        config = PeerRequirementsSettings.load()
        config.require_verification_to_publish = True
        config.save()

        user = make_peer(is_verified=False)
        assert "not_verified" in eligibility_failures(user)

    def test_verification_requirement_met(self):
        config = PeerRequirementsSettings.load()
        config.require_verification_to_publish = True
        config.save()

        user = make_peer(is_verified=True)
        assert is_eligible_peer(user) is True


def _approved_request(peer, *, start, minutes):
    meeting = create_meeting(peer=peer)
    request = MeetingRequest(
        meeting=meeting,
        support_seeker=UserFactory(),
        requested_start_time=start,
        requested_duration_minutes=minutes,
    )
    request.start()  # PAY_AFTER_JOIN -> APPROVED
    request.save()
    return request


class TestAvailableSlots:
    def test_no_windows_means_no_slots(self):
        assert available_slots(make_peer()) == []

    def test_one_off_window(self):
        peer = make_peer()
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)
        make_availability(peer, start=start, end=end)

        assert available_slots(peer) == [(start, end)]

    def test_recurring_daily_expands(self):
        peer = make_peer()
        base = (timezone.now() + timedelta(days=1)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        make_availability(
            peer,
            start=base,
            end=base + timedelta(hours=1),
            occurrence="daily",
            occurrence_starts_at=base,
            occurrence_ends_at=base + timedelta(days=2),
        )

        slots = available_slots(peer)
        assert len(slots) == EXPECTED_DAILY_SLOTS
        assert slots[0] == (base, base + timedelta(hours=1))

    def test_overnight_recurring_window(self):
        peer = make_peer()
        base = (timezone.now() + timedelta(days=1)).replace(
            hour=22,
            minute=0,
            second=0,
            microsecond=0,
        )
        make_availability(
            peer,
            start=base,
            end=base + timedelta(hours=4),
            occurrence="daily",
            occurrence_starts_at=base,
            occurrence_ends_at=base + timedelta(days=1),
        )

        start, end = available_slots(peer)[0]
        assert start == base
        assert end == base + timedelta(hours=4)

    def test_booked_time_is_removed(self):
        peer = make_peer()
        base = (timezone.now() + timedelta(days=2)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        make_availability(
            peer,
            start=base,
            end=base + timedelta(hours=3),
        )
        _approved_request(peer, start=base + timedelta(hours=1), minutes=60)

        assert available_slots(peer) == [
            (base, base + timedelta(hours=1)),
            (base + timedelta(hours=2), base + timedelta(hours=3)),
        ]

    def test_fully_booked_slot_is_removed(self):
        peer = make_peer()
        base = (timezone.now() + timedelta(days=2)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        make_availability(peer, start=base, end=base + timedelta(hours=1))
        _approved_request(peer, start=base, minutes=60)

        assert available_slots(peer) == []


class TestCalendarSync:
    def _window(self, peer):
        start = (timezone.now() + timedelta(days=2)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        return make_availability(peer, start=start, end=start + timedelta(hours=1))

    def test_window_creates_available_event(self):
        peer = make_peer()
        window = self._window(peer)

        assert (
            CalendarEvent.objects.filter(
                source_type="availability",
                source_id=window.pk,
                kind="available",
            ).count()
            == 1
        )

    def test_deleting_window_removes_event(self):
        peer = make_peer()
        window = self._window(peer)
        window.delete()

        assert not CalendarEvent.objects.filter(
            source_type="availability",
            source_id=window.pk,
        ).exists()


class TestPeerCalendarEvents:
    def _request(self, viewer, profile=None):
        request = RequestFactory().get("/")
        request.user = viewer
        if profile is not None:
            request.daisie_path_params = {"pk": profile.pk}
        return request

    def _window(self, peer):
        start = (timezone.now() + timedelta(days=2)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        return make_availability(peer, start=start, end=start + timedelta(hours=1))

    def test_owner_sees_events(self):
        peer = make_peer()
        self._window(peer)

        events = peer_calendar_events(self._request(peer, peer.peer_profile))
        assert events.count() == 1

    def test_unpublished_calendar_hidden_from_others(self):
        peer = make_peer()
        self._window(peer)
        viewer = make_peer()

        events = peer_calendar_events(self._request(viewer, peer.peer_profile))
        assert events.count() == 0

    def test_published_calendar_shows_availability(self):
        peer = make_peer()
        profile, _created = UserProfile.objects.get_or_create(user=peer)
        profile.show_calendar = True
        profile.save()
        self._window(peer)
        viewer = make_peer()

        events = peer_calendar_events(self._request(viewer, peer.peer_profile))
        assert [event.display_title for event in events] == ["Available"]
