from unittest.mock import patch

import pytest

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.payments.services import create_express_dashboard_link
from neuromancers_network.payments.services import create_webhook_endpoint
from neuromancers_network.payments.services import ensure_payment_profile
from neuromancers_network.payments.services import ensure_stripe_account
from neuromancers_network.users.tests.factories import AccountFactory
from neuromancers_network.users.tests.factories import CustomerFactory
from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PUBLISHABLE_KEY = "pk_test_123"
SECRET_KEY = "sk_test_123"  # noqa: S105
EXISTING_ACCOUNT_ID = "acct_existing"
NEW_ACCOUNT_ID = "acct_new"
DASHBOARD_URL = "https://dashboard.stripe.com/express"
WEBHOOK_SECRET = "whsec_123"  # noqa: S105


def configure_stripe():
    config = StripeSettings.load()
    config.publishable_key = PUBLISHABLE_KEY
    config.secret_key = SECRET_KEY
    config.save()
    return config


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


class TestCreateWebhookEndpoint:
    def test_stores_secret(self):
        configure_stripe()

        with (
            patch(
                "neuromancers_network.payments.services.stripe.WebhookEndpoint.create",
            ) as create_endpoint,
            patch(
                "neuromancers_network.payments.services."
                "StripeWebhookEndpoint.sync_from_stripe_data",
            ),
        ):
            create_endpoint.return_value = type(
                "Endpoint",
                (),
                {"secret": WEBHOOK_SECRET},
            )()
            secret = create_webhook_endpoint(url="https://example.com/hook/")

        assert secret == WEBHOOK_SECRET
        assert StripeSettings.load().webhook_secret == WEBHOOK_SECRET
