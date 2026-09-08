import pytest
from djstripe.enums import SubscriptionStatus

from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory

pytestmark = pytest.mark.django_db


def make_payment_profile(
    *,
    subscription_status=SubscriptionStatus.active,
    kyc_completed=True,
):
    payment_profile = PaymentProfileFactory(kyc_completed=kyc_completed)
    if subscription_status is not None:
        PeerSubscriptionFactory(
            payment_profile=payment_profile,
            subscription__status=subscription_status,
        )
    return payment_profile


class TestHasActiveSubscription:
    def test_returns_false_without_subscription(self):
        payment_profile = make_payment_profile(subscription_status=None)
        assert payment_profile.has_active_subscription is False

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
    def test_returns_false_for_inactive_statuses(self, status):
        payment_profile = make_payment_profile(subscription_status=status)
        assert payment_profile.has_active_subscription is False

    @pytest.mark.parametrize(
        "status",
        [SubscriptionStatus.active, SubscriptionStatus.trialing],
    )
    def test_returns_true_for_active_statuses(self, status):
        payment_profile = make_payment_profile(subscription_status=status)
        assert payment_profile.has_active_subscription is True
