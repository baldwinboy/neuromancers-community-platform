import pytest
from djstripe.enums import SubscriptionStatus

from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def make_peer(
    *,
    is_approved=True,
    subscription_status=SubscriptionStatus.active,
    kyc_completed=True,
    is_verified=False,
):
    """Build a user wired up with the full peer lifecycle state."""
    user = UserFactory()
    PeerProfileFactory(user=user, is_approved=is_approved, is_verified=is_verified)
    payment_profile = PaymentProfileFactory(user=user, kyc_completed=kyc_completed)
    if subscription_status is not None:
        PeerSubscriptionFactory(
            payment_profile=payment_profile,
            subscription__status=subscription_status,
        )
    return user


class TestIsPeer:
    def test_no_peer_profile(self, user):
        assert user.is_peer is False

    def test_unapproved_peer_profile(self):
        user = UserFactory()
        PeerProfileFactory(user=user, is_approved=False)
        assert user.is_peer is False

    def test_approved_without_payment_profile(self):
        user = UserFactory()
        PeerProfileFactory(user=user, is_approved=True)
        assert user.is_peer is False

    def test_no_peer_subscription(self):
        user = make_peer(subscription_status=None)
        assert user.is_peer is False

    @pytest.mark.parametrize(
        "status",
        [
            SubscriptionStatus.canceled,
            SubscriptionStatus.past_due,
            SubscriptionStatus.incomplete,
            SubscriptionStatus.unpaid,
            SubscriptionStatus.paused,
        ],
    )
    def test_inactive_subscription_statuses(self, status):
        user = make_peer(subscription_status=status)
        assert user.is_peer is False

    @pytest.mark.parametrize(
        "status",
        [
            SubscriptionStatus.active,
            SubscriptionStatus.trialing,
        ],
    )
    def test_active_subscription_statuses(self, status):
        user = make_peer(subscription_status=status)
        assert user.is_peer is True

    def test_kyc_incomplete(self):
        user = make_peer(kyc_completed=False)
        assert user.is_peer is False


class TestIsVerifiedPeer:
    def test_verified_but_not_peer(self):
        user = make_peer(is_verified=True, kyc_completed=False)
        assert user.is_verified_peer is False

    def test_peer_not_verified(self):
        user = make_peer(is_verified=False)
        assert user.is_peer is True
        assert user.is_verified_peer is False

    def test_verified_peer(self):
        user = make_peer(is_verified=True)
        assert user.is_peer is True
        assert user.is_verified_peer is True

    def test_no_peer_profile(self, user):
        assert user.is_verified_peer is False
