from types import SimpleNamespace
from unittest.mock import patch

import pytest
from djstripe.enums import SubscriptionStatus

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.payments.models.profile import StripeConnectOnboardingLink
from neuromancers_network.payments.services import create_express_dashboard_link
from neuromancers_network.payments.services import ensure_payment_profile
from neuromancers_network.payments.services import ensure_stripe_account
from neuromancers_network.users.tests.factories import AccountFactory
from neuromancers_network.users.tests.factories import CustomerFactory
from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PUBLISHABLE_KEY = "pk_test_123"
SECRET_KEY = "sk_test_123"  # noqa: S105
EXISTING_ACCOUNT_ID = "acct_existing"
NEW_ACCOUNT_ID = "acct_new"
DASHBOARD_URL = "https://dashboard.stripe.com/express"


def configure_stripe():
    config = StripeSettings.load()
    config.publishable_key = PUBLISHABLE_KEY
    config.secret_key = SECRET_KEY
    config.save()
    return config


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
        StripeSettings.objects.create(secret_key=SECRET_KEY)
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


class TestEnsureStripeAccount:
    def test_returns_existing_account(self):
        profile = PaymentProfileFactory(
            stripe_connect_account_id=AccountFactory(id=EXISTING_ACCOUNT_ID),
        )

        account = ensure_stripe_account(profile.user)

        assert account.id == EXISTING_ACCOUNT_ID

    def test_creates_account_and_persists(self):
        configure_stripe()
        profile = PaymentProfileFactory(stripe_connect_account_id=None)

        with (
            patch(
                "neuromancers_network.payments.services.stripe.Account.create",
            ) as create_account,
            patch(
                "neuromancers_network.payments.services.StripeAccount.sync_from_stripe_data",
            ) as sync_account,
        ):
            create_account.return_value = {"id": NEW_ACCOUNT_ID}
            sync_account.return_value = AccountFactory(id=NEW_ACCOUNT_ID)
            account = ensure_stripe_account(profile.user)

        profile.refresh_from_db()
        assert account.id == NEW_ACCOUNT_ID
        assert profile.stripe_connect_account_id_id == NEW_ACCOUNT_ID

    def test_bootstraps_profile_for_new_user(self):
        configure_stripe()
        user = UserFactory()

        with (
            patch(
                "neuromancers_network.payments.services.stripe.Customer.create",
            ) as create_customer,
            patch(
                "neuromancers_network.payments.services."
                "StripeCustomer.sync_from_stripe_data",
            ) as sync_customer,
            patch(
                "neuromancers_network.payments.services.stripe.Account.create",
            ) as create_account,
            patch(
                "neuromancers_network.payments.services.StripeAccount.sync_from_stripe_data",
            ) as sync_account,
        ):
            create_customer.return_value = {"id": "cus_boot"}
            sync_customer.return_value = CustomerFactory(id="cus_boot")
            create_account.return_value = {"id": NEW_ACCOUNT_ID}
            sync_account.return_value = AccountFactory(id=NEW_ACCOUNT_ID)
            account = ensure_stripe_account(user)

        user.refresh_from_db()
        assert account.id == NEW_ACCOUNT_ID
        assert user.payment_profile.stripe_customer_id_id == "cus_boot"


class TestEnsurePaymentProfile:
    def test_returns_existing_profile(self):
        profile = PaymentProfileFactory()

        assert ensure_payment_profile(profile.user) == profile

    def test_creates_profile_and_customer(self):
        configure_stripe()
        user = UserFactory()

        with (
            patch(
                "neuromancers_network.payments.services.stripe.Customer.create",
            ) as create_customer,
            patch(
                "neuromancers_network.payments.services."
                "StripeCustomer.sync_from_stripe_data",
            ) as sync_customer,
        ):
            create_customer.return_value = {"id": "cus_new"}
            sync_customer.return_value = CustomerFactory(id="cus_new")
            profile = ensure_payment_profile(user)

        assert profile.user == user
        assert profile.stripe_customer_id_id == "cus_new"
        assert user.payment_profile == profile

    def test_requires_stripe_configuration(self):
        user = UserFactory()
        config = StripeSettings.load()
        config.secret_key = ""
        config.save()

        with pytest.raises(ValueError, match="secret key"):
            ensure_payment_profile(user)


class TestExpressDashboardLink:
    def test_returns_login_link(self):
        configure_stripe()
        profile = PaymentProfileFactory(
            stripe_connect_account_id=AccountFactory(id=EXISTING_ACCOUNT_ID),
        )

        with patch(
            "neuromancers_network.payments.services.stripe.Account.create_login_link",
        ) as create_link:
            create_link.return_value = type("Link", (), {"url": DASHBOARD_URL})()
            url = create_express_dashboard_link(profile)

        assert url == DASHBOARD_URL

    def test_without_account_raises(self):
        configure_stripe()
        profile = PaymentProfileFactory(stripe_connect_account_id=None)

        with pytest.raises(ValueError, match="no connected Stripe account"):
            create_express_dashboard_link(profile)


def make_event(account_id: str, account_data: dict | None = None):
    payload = {"id": account_id}
    if account_data:
        payload.update(account_data)
    return SimpleNamespace(
        data={"object": payload},
        default_api_key="sk_test",
    )


class TestAccountUpdatedSignal:
    def test_marks_kyc_completed_when_account_is_fully_onboarded(self):
        account = AccountFactory(id="acct_123")
        payment_profile = PaymentProfileFactory(
            stripe_connect_account_id=account,
            kyc_completed=False,
        )
        event = make_event(
            "acct_123",
            {
                "charges_enabled": True,
                "payouts_enabled": True,
                "details_submitted": True,
                "requirements": {
                    "currently_due": [],
                    "eventually_due": [],
                    "past_due": [],
                },
            },
        )

        with patch(
            "neuromancers_network.payments.signals.StripeAccount.sync_from_stripe_data",
        ) as sync_account:
            from neuromancers_network.payments.signals import (  # noqa: PLC0415
                handle_account_updated,
            )

            handle_account_updated(sender=None, event=event)

        payment_profile.refresh_from_db()
        assert payment_profile.kyc_completed is True
        sync_account.assert_called_once()

    def test_leaves_kyc_incomplete_when_requirements_remain(self):
        account = AccountFactory(id="acct_456")
        payment_profile = PaymentProfileFactory(
            stripe_connect_account_id=account,
            kyc_completed=False,
        )
        event = make_event(
            "acct_456",
            {
                "charges_enabled": False,
                "payouts_enabled": False,
                "details_submitted": False,
                "requirements": {
                    "currently_due": ["external_account"],
                    "eventually_due": [],
                    "past_due": [],
                },
            },
        )

        from neuromancers_network.payments.signals import (  # noqa: PLC0415
            handle_account_updated,
        )

        with patch(
            "neuromancers_network.payments.signals.StripeAccount.sync_from_stripe_data",
        ):
            handle_account_updated(sender=None, event=event)

        payment_profile.refresh_from_db()
        assert payment_profile.kyc_completed is False
