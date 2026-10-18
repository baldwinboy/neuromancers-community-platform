"""Resolve Stripe Checkout charge parameters from the admin charge settings.

A single helper keeps ``Booking`` and ``MeetingRequest`` checkout creation in
agreement. The admin-selected charge type decides whether the connected account
is the merchant of record (direct) or whether funds move via ``transfer_data``
(destination).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP
from decimal import Decimal

from neuromancers_network.core.models import LocalizationSettings
from neuromancers_network.core.models import StripeSettings


def adaptive_pricing_for_source(source: str) -> dict | None:
    """Return Stripe adaptive-pricing settings for an exchange-rate source."""
    if source == "stripe":
        return {"enabled": True}
    return None


def adaptive_pricing(request=None):
    """Return Stripe adaptive-pricing settings, or ``None`` when disabled."""
    source = LocalizationSettings.load(request).exchange_rate_source
    return adaptive_pricing_for_source(source)


@dataclass(frozen=True)
class ChargePlan:
    """Stripe Checkout parameters resolved from the configured charge type."""

    stripe_account: str | None
    payment_intent_data: dict | None
    automatic_tax: dict | None


def build_charge_plan(
    *,
    amount_minor: int,
    destination: str | None,
    stripe_settings: StripeSettings,
) -> ChargePlan:
    """Resolve Checkout parameters for the configured charge type.

    Raises ``ValueError`` when the charge type needs a connected account but the
    peer has none. ``automatic_tax`` is enabled only when ``tax_mode`` is
    ``stripe_tax``.
    """
    fee_percent = Decimal(stripe_settings.application_fee or 0)
    application_fee_amount = int(
        (Decimal(amount_minor) * fee_percent / Decimal(100)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        ),
    )
    automatic_tax = (
        {"enabled": True}
        if stripe_settings.tax_mode == StripeSettings.TaxMode.STRIPE_TAX
        else None
    )

    charge_type = stripe_settings.charge_type
    if not destination:
        message = "Peer has no connected Stripe account"
        raise ValueError(message)

    if charge_type == StripeSettings.ChargeType.DESTINATION:
        payment_intent_data = {
            "application_fee_amount": application_fee_amount,
            "transfer_data": {"destination": destination},
        }
        return ChargePlan(
            stripe_account=None,
            payment_intent_data=payment_intent_data,
            automatic_tax=automatic_tax,
        )

    return ChargePlan(
        stripe_account=destination,
        payment_intent_data={"application_fee_amount": application_fee_amount},
        automatic_tax=automatic_tax,
    )


def build_refund_kwargs(
    *,
    stripe_settings: StripeSettings,
    destination: str | None,
) -> dict:
    """Resolve Stripe Refund parameters for the configured charge type.

    Direct charges refund on the connected account; destination charges reverse
    the transfer. Raises ``ValueError`` when a direct refund has no connected
    account.
    """
    charge_type = stripe_settings.charge_type
    if charge_type == StripeSettings.ChargeType.DESTINATION:
        return {"reverse_transfer": True, "refund_application_fee": True}
    if not destination:
        message = "Peer has no connected Stripe account"
        raise ValueError(message)
    return {"stripe_account": destination, "refund_application_fee": True}
