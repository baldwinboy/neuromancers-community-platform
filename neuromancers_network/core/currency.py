"""Display-currency helpers driven by :class:`LocalizationSettings`."""

from __future__ import annotations

from decimal import Decimal
from decimal import InvalidOperation

from babel.numbers import format_currency as babel_format_currency
from django.utils import translation

from neuromancers_network.core.i18n import active_currency
from neuromancers_network.core.i18n import get_localization

_TWO_PLACES = Decimal("0.01")
DEFAULT_CURRENCY = "GBP"


def display_currency() -> str:
    """Return the ISO 4217 code configured for display."""
    return active_currency()


def convert_amount(
    amount,
    *,
    source_currency: str,
    target_currency: str | None = None,
) -> Decimal:
    """Convert *amount* for display using the configured exchange rates.

    ``stripe`` (adaptive pricing) converts at checkout, so this helper returns
    the amount unchanged for that source. ``manual``/``fixed`` sources use the
    admin-supplied ``manual_exchange_rates`` mapping and fall back to the
    original amount when no rate is configured.
    """
    value = Decimal(str(amount))
    data = get_localization()
    source = source_currency.upper()
    target = (target_currency or data.get("display_currency", "GBP")).upper()
    if source == target or data.get("exchange_rate_source", "stripe") == "stripe":
        return _quantize(value)

    rates = data.get("manual_exchange_rates") or {}
    rate = rates.get(target)
    if rate is None:
        return _quantize(value)
    try:
        factor = Decimal(str(rate))
    except InvalidOperation:
        return _quantize(value)
    return _quantize(value * factor)


def format_amount(amount, *, currency=None, locale=None) -> str:
    """Format *amount* in the active locale and display currency."""
    code = (currency or display_currency() or DEFAULT_CURRENCY).upper()
    language = locale or translation.get_language() or "en"
    value = Decimal(str(amount))
    try:
        return babel_format_currency(value, code, locale=language)
    except Exception:  # noqa: BLE001 - fall back for unknown locale/currency
        return f"{value:.2f} {code}"


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES)
