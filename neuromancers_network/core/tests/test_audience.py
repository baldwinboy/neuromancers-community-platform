import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from neuromancers_network.core import audience
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.models import StaffState
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def rf() -> RequestFactory:
    return RequestFactory()


def make_request(rf, user, params=None):
    request = rf.get("/")
    request.user = user
    if params:
        request.daisie_path_params = params
    return request


class TestBasicPredicates:
    def test_anonymous(self, rf):
        request = rf.get("/")
        request.user = AnonymousUser()

        assert audience.is_authenticated(request) is False
        assert audience.is_peer(request) is False
        assert audience.is_moderator(request) is False

    def test_authenticated(self, rf, user):
        assert audience.is_authenticated(make_request(rf, user)) is True

    def test_moderator(self, rf):
        staff = UserFactory(staff_state=StaffState.ACTIVE)

        assert audience.is_moderator(make_request(rf, staff)) is True
        assert audience.is_moderator(make_request(rf, UserFactory())) is False


class TestPeerOwner:
    def test_anonymous(self, rf):
        request = rf.get("/")
        request.user = AnonymousUser()

        assert audience.is_peer_owner(request) is False

    def test_non_peer_viewing_own_profile(self, rf):
        user = UserFactory()
        request = make_request(rf, user, {"username": user.username})

        assert audience.is_peer_owner(request) is False

    def test_peer_viewing_own_profile(self, rf):
        peer = make_peer()
        request = make_request(rf, peer, {"username": peer.username})

        assert audience.is_peer_owner(request) is True

    def test_peer_viewing_other_profile(self, rf):
        peer = make_peer()
        other = UserFactory()
        request = make_request(rf, peer, {"username": other.username})

        assert audience.is_peer_owner(request) is False

    def test_moderator_viewing_other_profile(self, rf):
        staff = UserFactory(staff_state=StaffState.ACTIVE)
        other = UserFactory()
        request = make_request(rf, staff, {"username": other.username})

        assert audience.is_peer_owner(request) is False


class TestOwnProfile:
    def test_own_profile(self, rf, user):
        request = make_request(rf, user, {"username": user.username})

        assert audience.is_own_profile(request) is True
        assert audience.is_own_profile_or_moderator(request) is True

    def test_other_profile(self, rf, user):
        other = UserFactory()
        request = make_request(rf, user, {"username": other.username})

        assert audience.is_own_profile(request) is False

    def test_moderator_sees_any_profile(self, rf):
        staff = UserFactory(staff_state=StaffState.ACTIVE)
        other = UserFactory()
        request = make_request(rf, staff, {"username": other.username})

        assert audience.is_own_profile(request) is False
        assert audience.is_own_profile_or_moderator(request) is True


class TestMeetingPredicates:
    def test_host(self, rf):
        peer = make_peer()
        meeting = create_meeting(peer=peer)
        request = make_request(rf, peer, {"meeting_pk": meeting.pk})

        assert audience.is_meeting_host(request) is True
        assert audience.is_meeting_participant(request) is True

    def test_non_host(self, rf):
        peer = make_peer()
        meeting = create_meeting(peer=peer)
        request = make_request(rf, UserFactory(), {"meeting_pk": meeting.pk})

        assert audience.is_meeting_host(request) is False


class TestTosAcceptance:
    def test_needs_acceptance_when_not_accepted(self, rf):
        request = make_request(rf, UserFactory(accepted_tos=False))

        assert audience.needs_tos_acceptance(request) is True

    def test_no_need_when_already_accepted(self, rf):
        request = make_request(rf, UserFactory(accepted_tos=True))

        assert audience.needs_tos_acceptance(request) is False

    def test_anonymous_does_not_need(self, rf):
        request = rf.get("/")
        request.user = AnonymousUser()

        assert audience.needs_tos_acceptance(request) is False

    def test_queryset_selects_pending_members(self):
        pending = UserFactory(accepted_tos=False)
        UserFactory(accepted_tos=True)

        assert list(audience.needs_tos_acceptance_users()) == [pending]
