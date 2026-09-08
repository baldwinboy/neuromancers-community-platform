from types import SimpleNamespace
from unittest.mock import patch

import pytest

from neuromancers_network.users.tests.factories import AccountFactory
from neuromancers_network.users.tests.factories import PaymentProfileFactory

pytestmark = pytest.mark.django_db


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

        from neuromancers_network.payments.signals import (  # noqa: PLC0415
            handle_account_updated,
        )

        with patch(
            "neuromancers_network.payments.signals.StripeAccount.sync_from_stripe_data",
        ) as sync_account:
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

        handle_account_updated(sender=None, event=event)

        payment_profile.refresh_from_db()
        assert payment_profile.kyc_completed is False
