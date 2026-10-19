from __future__ import annotations

from decimal import Decimal

import pytest
from django.forms.models import model_to_dict
from django.http import QueryDict

from neuromancers_network.core.currency import base_conversion
from neuromancers_network.core.forms import LocalizationSettingsForm
from neuromancers_network.core.models import LocalizationSettings
from neuromancers_network.core.widgets import KeyValueWidget

pytestmark = pytest.mark.django_db


class TestBaseConversion:
    def test_same_currency_is_one_to_one(self):
        base, amount, rate = base_conversion(10, "GBP")

        assert base == "GBP"
        assert amount == Decimal("10.00")
        assert rate == Decimal("1")

    def test_stripe_conversion_amount_wins(self):
        base, amount, rate = base_conversion(
            10,
            "USD",
            stripe_conversion={
                "currency": "GBP",
                "amount": 800,
                "source_currency": "USD",
                "target_currency": "GBP",
            },
        )

        assert base == "GBP"
        assert amount == Decimal("8.00")
        assert rate == Decimal("0.80000000")

    def test_stripe_fx_rate_base_to_presentment(self):
        _base, amount, rate = base_conversion(
            10,
            "USD",
            stripe_conversion={
                "fx_rate": "1.25",
                "source_currency": "GBP",
                "target_currency": "USD",
            },
        )

        assert amount == Decimal("8.00")
        assert rate == Decimal("0.80000000")

    def test_stripe_fx_rate_presentment_to_base(self):
        _base, amount, rate = base_conversion(
            10,
            "USD",
            stripe_conversion={
                "fx_rate": "0.8",
                "source_currency": "USD",
                "target_currency": "GBP",
            },
        )

        assert amount == Decimal("8.00")
        assert rate == Decimal("0.80000000")

    def test_unknown_conversion_returns_no_rate(self):
        base, amount, rate = base_conversion(10, "USD")

        assert base == "GBP"
        assert amount == Decimal("10.00")
        assert rate is None


class TestKeyValueWidget:
    def test_parses_repeated_pairs(self):
        data = QueryDict(
            "manual_exchange_rates_keys=EUR"
            "&manual_exchange_rates_keys="
            "&manual_exchange_rates_values=1.2"
            "&manual_exchange_rates_values=",
        )

        result = KeyValueWidget().value_from_datadict(
            data,
            {},
            "manual_exchange_rates",
        )

        assert result == {"EUR": "1.2"}

    def test_form_round_trip(self):
        config = LocalizationSettings.load()
        data = model_to_dict(config)
        data.pop("manual_exchange_rates", None)
        data["manual_exchange_rates_keys"] = ["EUR"]
        data["manual_exchange_rates_values"] = ["1.2"]
        form = LocalizationSettingsForm(data=data, instance=config)

        assert form.is_valid(), form.errors
        assert form.cleaned_data["manual_exchange_rates"] == {"EUR": "1.2"}
