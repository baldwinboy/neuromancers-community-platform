import logging

import stripe
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import PaymentIntent as StripePaymentIntent
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
