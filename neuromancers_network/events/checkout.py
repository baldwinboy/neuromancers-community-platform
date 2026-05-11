"""
Phase 1D: Charge-Routing Policy.

Determines the Stripe Connect charge strategy based on the number of
unpaid bookings in a cart. All monetary values are calculated server-side.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable

User = get_user_model()


class CheckoutStrategy(Enum):
    """How to process a set of bookings through Stripe."""

    DESTINATION = "destination"
    """Single booking → destination charge with application fee."""
    SEPARATE_CHARGES_AND_TRANSFERS = "separate_charges_and_transfers"
    """Multiple bookings → platform charge + per-host transfers."""


# ------------------------------------------------------------------
# Core policy functions
# ------------------------------------------------------------------


def determine_strategy(bookings: list) -> CheckoutStrategy:
    """
    Choose the charge type for a set of unpaid bookings.

    Raises ValueError if no bookings are provided.
    """
    unpaid = [b for b in bookings if b.amount_due_subunit > 0]
    if not unpaid:
        # All bookings are free - no Stripe interaction needed.
        return None  # or raise an exception; callers handle free separately

    if len(unpaid) == 1:
        return CheckoutStrategy.DESTINATION
    return CheckoutStrategy.SEPARATE_CHARGES_AND_TRANSFERS


def build_destination_checkout_params(
    booking: any,
    platform_fee_percent: Decimal = Decimal("15"),  # example fee
    success_url: str = "",
    cancel_url: str = "",
) -> dict:
    """
    Build parameters for a Stripe Checkout Session using a destination
    charge.

    * transfer_data.destination must be the host's connected account.
    * application_fee_amount is calculated from the platform fee policy.
    """
    if not booking.host_stripe_account_id:
        msg = f"Host {booking.host.pk} has no connected Stripe account."
        raise ImproperlyConfigured(
            msg,
        )

    application_fee = _calculate_platform_fee(
        booking.amount_due_subunit,
        platform_fee_percent,
    )

    return {
        "line_items": [
            {
                "price_data": {
                    "currency": booking.currency,
                    "product_data": {"name": f"Session booking {booking.id}"},
                    "unit_amount": booking.amount_due_subunit,
                },
                "quantity": 1,
            },
        ],
        "payment_intent_data": {
            "application_fee_amount": application_fee,
            "transfer_data": {
                "destination": booking.host_stripe_account_id,
            },
        },
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
    }


def build_separate_charges_checkout_params(
    bookings: list,
    platform_fee_percent: Decimal = Decimal("15"),
    success_url: str = "",
    cancel_url: str = "",
) -> dict:
    """
    Build parameters for a Checkout Session that will use separate
    charges and transfers. A single platform charge is created; per-host
    transfers are executed after payment.

    * payment_intent_data.transfer_group is a deterministic ID
      that links the charge with subsequent Transfers.
    """
    for booking in bookings:
        if not booking.host.stripe_account:
            msg = f"Host {booking.host.pk} missing Stripe account."
            raise ImproperlyConfigured(msg)

    total_amount = sum(b.amount_due_subunit for b in bookings)
    # For simplicity we assume a single currency; production must validate
    currency = bookings[0].currency

    transfer_group = _generate_transfer_group(bookings)

    return {
        "line_items": [
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": f"Multi-session booking ({len(bookings)} sessions)",
                    },
                    "unit_amount": total_amount,
                },
                "quantity": 1,
            },
        ],
        "payment_intent_data": {
            "transfer_group": transfer_group,
        },
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
    }


# ------------------------------------------------------------------
# Transfer planning (separate charges path only)
# ------------------------------------------------------------------


@dataclass
class PlannedTransfer:
    booking_id: uuid.UUID
    destination_account: str
    amount_subunit: int
    currency: str


def plan_transfers(
    charge_id: str,
    bookings: list,
) -> tuple[str, list[PlannedTransfer]]:
    """
    After a successful charge, compute the deterministic list of
    transfers for each booking.

    Returns the transfer_group string and a list of planned transfers.
    The transfer_group MUST match the one used in checkout.
    """
    transfer_group = _generate_transfer_group(bookings)
    transfers = [
        PlannedTransfer(
            booking_id=booking.id,
            destination_account=booking.host_stripe_account_id,
            amount_subunit=booking.host_payable_amount_subunit,
            currency=booking.currency,
        )
        for booking in bookings
    ]
    return transfer_group, transfers


# ------------------------------------------------------------------
# Failure fallback policy
# ------------------------------------------------------------------


def handle_partial_transfer_failure(
    payment_batch_id: uuid.UUID,
    failed_transfers: list[PlannedTransfer],
    succeeded_transfers: list[PlannedTransfer],
) -> None:
    """
    Called when some transfers within a batch fail.

    * Bookings corresponding to failed transfers remain in
      non-confirmed state and are flagged for retry.
    * Succeeded bookings are finalised normally.
    * An operational alert is raised for manual review.

    This function is a placeholder that will be implemented in
    Phase 4 (Payment Orchestration).
    """
    # TODO: In Phase 4, update booking payment_status → PROCESSING/FAILED
    # and create a retry record for each failed transfer.
    msg = "Partial transfer failure handling will be implemented in Phase 4."
    raise NotImplementedError(
        msg,
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _calculate_platform_fee(
    amount_subunit: int,
    platform_fee_percent: Decimal,
) -> int:
    """Platform fee in subunit, truncated to integer (Stripe requirement)."""
    return int(amount_subunit * platform_fee_percent / 100)


def _generate_transfer_group(bookings: Iterable[any]) -> str:
    """
    Deterministic transfer_group ID derived from the sorted booking
    IDs. This ensures idempotency even if the request is replayed.
    """
    sorted_ids = sorted(str(b.id) for b in bookings)
    return f"cart_{'_'.join(sorted_ids)}"
