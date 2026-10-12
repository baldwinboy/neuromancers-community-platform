"""Pure unit tests for the Stripe charge-parameter resolvers.

These cover the platform's charge-model decisions (direct / destination /
separate, tax mode and fee math) directly, without mocking the Stripe SDK.
"""

from __future__ import annotations

import pytest

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.payments.charges import build_charge_plan
from neuromancers_network.payments.charges import build_refund_kwargs

DESTINATION = "acct_peer"
FEE_PERCENT = 10
AMOUNT_MINOR = 2000


def make_settings(**overrides) -> StripeSettings:
    defaults = {
        "charge_type": StripeSettings.ChargeType.DIRECT,
        "tax_mode": StripeSettings.TaxMode.STRIPE_TAX,
        "application_fee": FEE_PERCENT,
    }
    defaults.update(overrides)
    return StripeSettings(**defaults)


class TestBuildChargePlan:
    def test_direct_charge_targets_connected_account(self):
        plan = build_charge_plan(
            amount_minor=AMOUNT_MINOR,
            destination=DESTINATION,
            stripe_settings=make_settings(),
        )

        assert plan.stripe_account == DESTINATION
        assert plan.payment_intent_data == {"application_fee_amount": 200}
        assert "transfer_data" not in plan.payment_intent_data
        assert plan.automatic_tax == {"enabled": True}

    def test_destination_charge_transfers_to_connected_account(self):
        plan = build_charge_plan(
            amount_minor=AMOUNT_MINOR,
            destination=DESTINATION,
            stripe_settings=make_settings(
                charge_type=StripeSettings.ChargeType.DESTINATION,
            ),
        )

        assert plan.stripe_account is None
        assert plan.payment_intent_data == {
            "application_fee_amount": 200,
            "transfer_data": {"destination": DESTINATION},
        }

    def test_separate_charge_has_no_fee_or_destination(self):
        plan = build_charge_plan(
            amount_minor=AMOUNT_MINOR,
            destination=DESTINATION,
            stripe_settings=make_settings(
                charge_type=StripeSettings.ChargeType.SEPARATE,
            ),
        )

        assert plan.stripe_account is None
        assert plan.payment_intent_data is None
        assert plan.automatic_tax == {"enabled": True}

    def test_tax_disabled_when_off(self):
        plan = build_charge_plan(
            amount_minor=AMOUNT_MINOR,
            destination=DESTINATION,
            stripe_settings=make_settings(tax_mode=StripeSettings.TaxMode.OFF),
        )

        assert plan.automatic_tax is None

    def test_fee_is_rounded_to_minor_units(self):
        plan = build_charge_plan(
            amount_minor=333,
            destination=DESTINATION,
            stripe_settings=make_settings(application_fee=15),
        )

        assert plan.payment_intent_data == {"application_fee_amount": 50}

    def test_fee_defaults_to_zero_when_unset(self):
        plan = build_charge_plan(
            amount_minor=AMOUNT_MINOR,
            destination=DESTINATION,
            stripe_settings=make_settings(application_fee=None),
        )

        assert plan.payment_intent_data == {"application_fee_amount": 0}

    @pytest.mark.parametrize(
        "charge_type",
        [StripeSettings.ChargeType.DIRECT, StripeSettings.ChargeType.DESTINATION],
    )
    def test_missing_destination_raises(self, charge_type):
        with pytest.raises(ValueError, match="no connected Stripe account"):
            build_charge_plan(
                amount_minor=AMOUNT_MINOR,
                destination=None,
                stripe_settings=make_settings(charge_type=charge_type),
            )


class TestBuildRefundKwargs:
    def test_direct_refund_targets_connected_account(self):
        kwargs = build_refund_kwargs(
            stripe_settings=make_settings(),
            destination=DESTINATION,
        )

        assert kwargs == {
            "stripe_account": DESTINATION,
            "refund_application_fee": True,
        }

    def test_destination_refund_reverses_transfer(self):
        kwargs = build_refund_kwargs(
            stripe_settings=make_settings(
                charge_type=StripeSettings.ChargeType.DESTINATION,
            ),
            destination=DESTINATION,
        )

        assert kwargs == {"reverse_transfer": True, "refund_application_fee": True}

    def test_separate_refund_has_no_extra_params(self):
        kwargs = build_refund_kwargs(
            stripe_settings=make_settings(
                charge_type=StripeSettings.ChargeType.SEPARATE,
            ),
            destination=DESTINATION,
        )

        assert kwargs == {}

    def test_direct_refund_without_destination_raises(self):
        with pytest.raises(ValueError, match="no connected Stripe account"):
            build_refund_kwargs(
                stripe_settings=make_settings(),
                destination=None,
            )
