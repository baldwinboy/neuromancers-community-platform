import logging

import stripe
from django_fsm import can_proceed
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Dispute as StripeDispute
from djstripe.models import PaymentIntent as StripePaymentIntent
from djstripe.models import Refund as StripeRefund
from djstripe.models import Session as StripeSession

from neuromancers_network.payments.webhooks import event_account_id
from neuromancers_network.payments.webhooks import sync_from_event

logger = logging.getLogger(__name__)


@djstripe_receiver("checkout.session.completed")
def handle_checkout_session_completed(sender, event, **kwargs):
    """Mark a meeting request or booking paid when Stripe Checkout completes."""
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    session_data = event.data.get("object", {})
    session_id = session_data.get("id")
    payment_intent_id = session_data.get("payment_intent")
    amount_total = session_data.get("amount_total")

    if not session_id:
        logger.warning("Ignoring checkout.session.completed without session id")
        return

    sync_from_event(StripeSession, session_data, event)

    if payment_intent_id:
        retrieve_kwargs = {"api_key": event.default_api_key}
        account_id = event_account_id(event)
        if account_id:
            retrieve_kwargs["stripe_account"] = account_id
        payment_intent = stripe.PaymentIntent.retrieve(
            payment_intent_id,
            **retrieve_kwargs,
        )
        sync_from_event(StripePaymentIntent, payment_intent, event)

    meeting_request = MeetingRequest.objects.filter(
        stripe_checkout_session_id=session_id,
    ).first()
    if meeting_request is not None:
        meeting_request.sync_payment_from_checkout(
            session_id,
            payment_intent_id,
            amount_total,
        )
        return

    booking = Booking.objects.filter(stripe_checkout_session_id=session_id).first()
    if booking is not None:
        if payment_intent_id and booking.stripe_payment_intent_id != payment_intent_id:
            booking.stripe_payment_intent_id = payment_intent_id
        if can_proceed(booking.mark_paid):
            booking.mark_paid()
        booking.save()
        booking.record_receipt()


@djstripe_receiver("payment_intent.succeeded")
def handle_payment_intent_succeeded(sender, event, **kwargs):
    """Sync the payment intent and refresh any stored hosted receipt."""
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415
    from neuromancers_network.payments.services import receipt_url_for  # noqa: PLC0415

    data = event.data.get("object", {})
    payment_intent_id = data.get("id")
    if not payment_intent_id:
        logger.warning("Ignoring payment_intent.succeeded without id")
        return

    sync_from_event(StripePaymentIntent, data, event)

    meeting_request = MeetingRequest.objects.filter(
        stripe_payment_intent_id=payment_intent_id,
    ).first()
    if meeting_request is not None:
        meeting_request.receipt_url = (
            receipt_url_for(payment_intent_id) or meeting_request.receipt_url
        )
        meeting_request.save(update_fields=["receipt_url", "updated_at"])

    booking = Booking.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
    if booking is not None:
        booking.record_receipt()


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

        sync_from_event(StripeRefund, refund_data, event)

        try:
            refund_request = RefundRequest.objects.get(stripe_refund_id=refund_id)
        except RefundRequest.DoesNotExist:
            continue

        if can_proceed(refund_request.mark_refunded):
            refund_request.mark_refunded()
            refund_request.save(update_fields=["status", "updated_at"])
        break


@djstripe_receiver(["charge.dispute.created", "charge.dispute.closed"])
def handle_charge_dispute(sender, event, **kwargs):
    """Sync the dispute onto the platform for the connected account."""
    dispute_data = event.data.get("object", {})
    if not dispute_data.get("id"):
        logger.warning("Ignoring %s without dispute id", event.type)
        return
    sync_from_event(StripeDispute, dispute_data, event)
