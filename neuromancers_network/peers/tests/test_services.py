import pytest

from neuromancers_network.peers.models.settings import PeerRequirementsSettings
from neuromancers_network.peers.services import eligibility_failures
from neuromancers_network.peers.services import is_eligible_peer
from neuromancers_network.peers.tests.factories import make_peer

pytestmark = pytest.mark.django_db


class TestEligibility:
    def test_unknown_user_is_not_eligible(self):
        assert is_eligible_peer(None) is False

    def test_user_without_peer_profile(self, user):
        assert is_eligible_peer(user) is False
        assert "not_approved" in eligibility_failures(user)

    def test_full_peer_is_eligible(self):
        assert is_eligible_peer(make_peer()) is True

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
