from unittest.mock import patch

import pytest
from djstripe.enums import SubscriptionStatus

from neuromancers_network.payments.models.profile import StripeConnectOnboardingLink
from neuromancers_network.users.tests.factories import AccountFactory
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


class TestStripeConnectOnboardingLink:
    def test_creates_account_link(self):
        payment_profile = PaymentProfileFactory(
            stripe_connect_account_id=AccountFactory(id="acct_123"),
        )
        with patch(
            "neuromancers_network.payments.models.profile.stripe.AccountLink.create",
        ) as create_link:
            create_link.return_value = type(
                "Link",
                (),
                {"url": "https://stripe.test/onboard"},
            )()
            result = payment_profile.create_stripe_onboarding_link(
                refresh_url="https://example.com/refresh",
                return_url="https://example.com/return",
            )

        assert result == StripeConnectOnboardingLink(
            account_id="acct_123",
            url="https://stripe.test/onboard",
        )
