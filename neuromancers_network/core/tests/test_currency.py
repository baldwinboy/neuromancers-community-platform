from decimal import Decimal

import pytest

from neuromancers_network.core.currency import convert_amount
from neuromancers_network.core.currency import display_currency
from neuromancers_network.core.currency import format_amount
from neuromancers_network.core.i18n import bust_localization_cache
from neuromancers_network.core.models import LocalizationSettings

pytestmark = pytest.mark.django_db


def configure(**kwargs):
    config = LocalizationSettings.load()
    for field, value in kwargs.items():
        setattr(config, field, value)
    config.save()
    bust_localization_cache()


class TestConvertAmount:
    def test_same_currency_unchanged(self):
        configure(display_currency="GBP")

        assert convert_amount(Decimal("10.00"), source_currency="GBP") == Decimal(
            "10.00",
        )

    def test_stripe_source_unchanged(self):
        configure(display_currency="EUR", exchange_rate_source="stripe")

        assert convert_amount(Decimal("10.00"), source_currency="GBP") == Decimal(
            "10.00",
        )

    def test_manual_rate_applied(self):
        configure(
            display_currency="EUR",
            exchange_rate_source="manual",
            manual_exchange_rates={"EUR": "1.2"},
        )

        assert convert_amount(Decimal("10.00"), source_currency="GBP") == Decimal(
            "12.00",
        )

    def test_missing_rate_falls_back(self):
        configure(
            display_currency="EUR",
            exchange_rate_source="manual",
            manual_exchange_rates={},
        )

        assert convert_amount(Decimal("10.00"), source_currency="GBP") == Decimal(
            "10.00",
        )


class TestDisplayCurrency:
    def test_display_currency(self):
        configure(display_currency="USD")

        assert display_currency() == "USD"


class TestFormatAmount:
    def test_gbp_in_english_locale(self):
        configure(display_currency="GBP")

        assert format_amount(Decimal("10"), locale="en_GB") == "£10.00"

    def test_eur_in_german_locale(self):
        configure(display_currency="EUR")

        formatted = format_amount(Decimal("10"), locale="de_DE")

        assert "€" in formatted
        assert "10,00" in formatted

    def test_explicit_currency_and_locale(self):
        formatted = format_amount(Decimal("5"), currency="USD", locale="en_US")

        assert formatted == "$5.00"
