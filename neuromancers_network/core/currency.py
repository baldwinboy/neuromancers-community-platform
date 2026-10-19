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
    rate=None,
) -> Decimal:
    """Convert *amount* from source to target currency.

    ``rate`` is an explicit source->target multiplier (for example a checkout
    rate persisted on an analytics row); it wins over the configured source.
    Otherwise ``stripe`` (adaptive pricing) is treated as already converted at
    checkout and returns the amount unchanged. ``manual``/``fixed`` sources use
    ``manual_exchange_rates``, accepting an explicit ``"SOURCE:TARGET"`` key
    first and the legacy ``{target: rate}`` key second. Invalid, non-positive
    or missing rates leave the amount unchanged.
    """
    if amount in (None, ""):
        return _quantize(Decimal("0"))
    value = Decimal(str(amount))
    data = get_localization()
    source = (source_currency or DEFAULT_CURRENCY).upper()
    target = (target_currency or data.get("display_currency", "GBP")).upper()
    if source == target:
        return _quantize(value)

    factor = _positive_rate(rate)
    if factor is not None:
        return _quantize(value * factor)

    if data.get("exchange_rate_source", "stripe") == "stripe":
        return _quantize(value)

    rates = data.get("manual_exchange_rates") or {}
    factor = _positive_rate(rates.get(f"{source}:{target}"))
    if factor is None:
        factor = _positive_rate(rates.get(target))
    if factor is None:
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


def _positive_rate(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        rate = Decimal(str(value))
    except InvalidOperation, ValueError:
        return None
    return rate if rate > 0 else None


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES)


RATE_PLACES = Decimal("0.00000001")


def base_conversion(
    amount,
    presentment_currency: str,
    *,
    stripe_conversion=None,
    base_currency: str | None = None,
):
    """Return ``(base_currency, base_amount, base_per_presentment_rate)``.

    Prefers Stripe's ``currency_conversion`` payload when it identifies the base
    currency, then its ``fx_rate`` with explicit source/target currencies, and
    finally the configured manual rates. ``rate`` is ``None`` when no conversion
    is known (the amount is returned unchanged and callers should not pretend a
    1:1 rate).
    """
    value = Decimal(str(amount or 0))
    presentment = (presentment_currency or DEFAULT_CURRENCY).upper()
    base = (base_currency or display_currency() or DEFAULT_CURRENCY).upper()
    if presentment == base:
        return base, _quantize(value), Decimal("1")

    conversion = stripe_conversion or {}
    cv_currency = (conversion.get("currency") or "").upper()
    cv_amount = conversion.get("amount")
    if cv_currency == base and cv_amount not in (None, ""):
        base_amount = _quantize(Decimal(str(cv_amount)) / 100)
        rate = (base_amount / value).quantize(RATE_PLACES) if value else None
        return base, base_amount, rate

    fx_rate = _positive_rate(conversion.get("fx_rate"))
    source = (conversion.get("source_currency") or "").upper()
    target = (conversion.get("target_currency") or "").upper()
    if fx_rate is not None:
        rate = None
        if source == base and target == presentment:
            rate = (Decimal("1") / fx_rate).quantize(RATE_PLACES)
        elif source == presentment and target == base:
            rate = fx_rate
        if rate is not None:
            return base, _quantize(value * rate), rate

    converted = convert_amount(
        value,
        source_currency=presentment,
        target_currency=base,
    )
    if converted == _quantize(value):
        return base, converted, None
    rate = (converted / value).quantize(RATE_PLACES) if value else None
    return base, converted, rate
