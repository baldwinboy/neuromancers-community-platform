import logging

import stripe
from django_fsm import can_proceed
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import PaymentIntent as StripePaymentIntent
from djstripe.models import Refund as StripeRefund
from djstripe.models import Session as StripeSession

logger = logging.getLogger(__name__)


@djstripe_receiver("checkout.session.completed")
def handle_checkout_session_completed(sender, event, **kwargs):
    """Mark a meeting request paid when Stripe Checkout completes."""
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    session_data = event.data.get("object", {})
    session_id = session_data.get("id")
    payment_intent_id = session_data.get("payment_intent")
    amount_total = session_data.get("amount_total")

    if not session_id:
        logger.warning("Ignoring checkout.session.completed without session id")
        return

    StripeSession.sync_from_stripe_data(session_data, api_key=event.default_api_key)

    try:
        request = MeetingRequest.objects.get(stripe_checkout_session_id=session_id)
    except MeetingRequest.DoesNotExist:
        logger.warning("No meeting request found for checkout session %s", session_id)
        return

    if payment_intent_id:
        payment_intent = stripe.PaymentIntent.retrieve(
            payment_intent_id,
            api_key=event.default_api_key,
        )
        StripePaymentIntent.sync_from_stripe_data(
            payment_intent,
            api_key=event.default_api_key,
        )

    request.sync_payment_from_checkout(session_id, payment_intent_id, amount_total)


@djstripe_receiver("charge.refunded")
def handle_charge_refunded(sender, event, **kwargs):
    """Mark a local refund request as refunded when Stripe confirms refund."""
    from neuromancers_network.meetings.models import RefundRequest  # noqa: PLC0415

    charge_data = event.data.get("object", {})
    refunds = charge_data.get("refunds", {}).get("data", [])

    if not refunds:
        logger.warning("Ignoring charge.refunded without refund data")
        return

    for refund_data in refunds:
        refund_id = refund_data.get("id")
        if not refund_id:
            continue

        StripeRefund.sync_from_stripe_data(refund_data, api_key=event.default_api_key)

        try:
            refund_request = RefundRequest.objects.get(stripe_refund_id=refund_id)
        except RefundRequest.DoesNotExist:
            continue

        if can_proceed(refund_request.mark_refunded):
            refund_request.mark_refunded()
            refund_request.save(update_fields=["status", "updated_at"])
        break
