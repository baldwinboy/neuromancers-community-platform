"""Resolve Stripe Checkout charge parameters from the admin charge settings.

A single helper keeps ``Booking`` and ``MeetingRequest`` checkout creation in
agreement. The admin-selected charge type decides whether the connected account
is the merchant of record (direct), whether funds move via ``transfer_data``
(destination) or stay on the platform account (separate fallback).
"""

from __future__ import annotations

from dataclasses import dataclass

from neuromancers_network.core.models import StripeSettings


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
    fee_percent = stripe_settings.application_fee or 0
    application_fee_amount = round(amount_minor * fee_percent / 100)
    automatic_tax = (
        {"enabled": True}
        if stripe_settings.tax_mode == StripeSettings.TaxMode.STRIPE_TAX
        else None
    )

    charge_type = stripe_settings.charge_type
    if charge_type == StripeSettings.ChargeType.SEPARATE:
        return ChargePlan(
            stripe_account=None,
            payment_intent_data=None,
            automatic_tax=automatic_tax,
        )

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
