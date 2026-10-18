import logging
from decimal import Decimal

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
        refs = _line_item_refs(session_data)
        if refs:
            _apply_line_item_amounts(session_id, session_data, refs, event)
            return
        # Legacy sessions created before per-item refs: mark the booking only.
        if payment_intent_id and booking.stripe_payment_intent_id != payment_intent_id:
            booking.stripe_payment_intent_id = payment_intent_id
        if can_proceed(booking.mark_paid):
            booking.mark_paid()
        booking.save()
        booking.record_receipt()


def _line_item_refs(session_data) -> list[str]:
    """Return the ordered record refs stored on the Checkout Session."""
    metadata = session_data.get("metadata") or {}
    raw = metadata.get("line_item_refs") or ""
    return [ref for ref in raw.split(",") if ref]


def _retrieve_line_items(session_id: str, event) -> list:
    """Fetch every line item for *session_id*, with the connected-account key."""
    account_id = event_account_id(event)
    items: list = []
    starting_after = None
    while True:
        if starting_after:
            page = stripe.checkout.Session.list_line_items(
                session_id,
                limit=100,
                starting_after=starting_after,
                api_key=event.default_api_key,
                stripe_account=account_id,
            )
        else:
            page = stripe.checkout.Session.list_line_items(
                session_id,
                limit=100,
                api_key=event.default_api_key,
                stripe_account=account_id,
            )
        items.extend(page.data)
        if not page.has_more or not page.data:
            return items
        starting_after = page.data[-1].id


def _apply_line_item_amounts(session_id, session_data, refs, event) -> None:
    """Apply each Stripe line item amount to its referenced record."""
    from neuromancers_network.payments.services import receipt_url_for  # noqa: PLC0415

    payment_intent_id = session_data.get("payment_intent") or ""
    receipt_url = receipt_url_for(payment_intent_id) if payment_intent_id else ""

    try:
        items = _retrieve_line_items(session_id, event)
    except Exception:
        logger.exception(
            "Could not retrieve line items for checkout session %s",
            session_id,
        )
        return

    if len(items) != len(refs):
        logger.error(
            "Line item/ref mismatch for checkout session %s: %d items, %d refs",
            session_id,
            len(items),
            len(refs),
        )
        return

    affected_bookings: set[int] = set()
    for ref, item in zip(refs, items, strict=True):
        amount_total = item.amount_total
        if amount_total is None:
            logger.error(
                "Line item %s for checkout session %s has no amount",
                item.id,
                session_id,
            )
            continue
        kind, _, raw_pk = ref.partition(":")
        if not raw_pk.isdigit():
            logger.error("Invalid line item ref %r for session %s", ref, session_id)
            continue
        pk = int(raw_pk)
        amount = Decimal(amount_total) / 100
        if kind == "request":
            booking_id = _apply_request_payment(
                pk,
                session_id,
                payment_intent_id,
                amount,
                receipt_url,
            )
            if booking_id is not None:
                affected_bookings.add(booking_id)
        elif kind == "booking":
            _apply_booking_payment(
                pk,
                session_id,
                payment_intent_id,
                amount,
                receipt_url,
            )
        else:
            logger.error("Unknown line item ref %r for session %s", ref, session_id)

    for booking_id in affected_bookings:
        _finalize_booking(booking_id, session_id, payment_intent_id, receipt_url)


def _apply_request_payment(
    pk,
    session_id,
    payment_intent_id,
    amount,
    receipt_url,
) -> int | None:
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    meeting_request = MeetingRequest.objects.filter(pk=pk).first()
    if meeting_request is None:
        logger.error(
            "Checkout session %s references missing request %s",
            session_id,
            pk,
        )
        return None
    meeting_request.stripe_checkout_session_id = session_id
    if payment_intent_id:
        meeting_request.stripe_payment_intent_id = payment_intent_id
    if receipt_url:
        meeting_request.receipt_url = receipt_url
    meeting_request.price_paid = amount
    if can_proceed(meeting_request.mark_paid):
        meeting_request.mark_paid()
    meeting_request.save(
        validate=False,
        update_fields=[
            "status",
            "stripe_checkout_session_id",
            "stripe_payment_intent_id",
            "receipt_url",
            "price_paid",
            "updated_at",
        ],
    )
    return meeting_request.booking_id


def _finalize_booking(
    booking_id,
    session_id,
    payment_intent_id,
    receipt_url,
) -> None:
    """Mark the parent booking paid and total it from its request amounts."""
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415

    booking = Booking.objects.filter(pk=booking_id).first()
    if booking is None:
        logger.error(
            "Checkout session %s references missing booking %s",
            session_id,
            booking_id,
        )
        return
    booking.stripe_checkout_session_id = session_id
    if payment_intent_id:
        booking.stripe_payment_intent_id = payment_intent_id
    if receipt_url:
        booking.receipt_url = receipt_url
    total = sum(
        (session.price_paid or Decimal("0")) for session in booking.sessions.all()
    )
    if total:
        booking.total_amount = total
    if can_proceed(booking.mark_paid):
        booking.mark_paid()
    booking.save(
        update_fields=[
            "status",
            "stripe_checkout_session_id",
            "stripe_payment_intent_id",
            "receipt_url",
            "total_amount",
            "updated_at",
        ],
    )


def _apply_booking_payment(
    pk,
    session_id,
    payment_intent_id,
    amount,
    receipt_url,
) -> None:
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415

    booking = Booking.objects.filter(pk=pk).first()
    if booking is None:
        logger.error(
            "Checkout session %s references missing booking %s",
            session_id,
            pk,
        )
        return
    booking.stripe_checkout_session_id = session_id
    if payment_intent_id:
        booking.stripe_payment_intent_id = payment_intent_id
    if receipt_url:
        booking.receipt_url = receipt_url
    booking.total_amount = amount
    if can_proceed(booking.mark_paid):
        booking.mark_paid()
    booking.save(
        update_fields=[
            "status",
            "stripe_checkout_session_id",
            "stripe_payment_intent_id",
            "receipt_url",
            "total_amount",
            "updated_at",
        ],
    )


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
