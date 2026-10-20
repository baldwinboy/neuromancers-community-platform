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


def _participants_for_payment_intent(payment_intent_id):
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    if not payment_intent_id:
        return None, None
    request_row = (
        MeetingRequest.objects.filter(stripe_payment_intent_id=payment_intent_id)
        .select_related("meeting", "support_seeker")
        .first()
    )
    if request_row is not None:
        return request_row.support_seeker, request_row.meeting.peer
    booking = (
        Booking.objects.filter(stripe_payment_intent_id=payment_intent_id)
        .select_related("meeting", "support_seeker")
        .first()
    )
    if booking is not None:
        return booking.support_seeker, booking.meeting.peer
    return None, None


def _record_item_ledger(  # noqa: PLR0913
    *,
    session_id,
    ref,
    amount_minor,
    currency,
    occurred_at,
    provider_object_id="",
    currency_conversion=None,
):
    from neuromancers_network.analytics.services import record_activity  # noqa: PLC0415
    from neuromancers_network.analytics.services import record_payment  # noqa: PLC0415
    from neuromancers_network.core.currency import base_conversion  # noqa: PLC0415
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    kind, _, raw_pk = ref.partition(":")
    if not raw_pk.isdigit():
        return
    pk = int(raw_pk)
    if kind == "request":
        target = (
            MeetingRequest.objects.filter(pk=pk)
            .select_related("meeting", "support_seeker")
            .first()
        )
        object_type = "meetingrequest"
    elif kind == "booking":
        target = (
            Booking.objects.filter(pk=pk)
            .select_related("meeting", "support_seeker")
            .first()
        )
        object_type = "booking"
    else:
        return
    if target is None:
        return
    amount = Decimal(amount_minor or 0) / 100
    base_currency, base_amount, rate = base_conversion(
        amount,
        currency,
        stripe_conversion=currency_conversion,
    )
    record_payment(
        session_id=session_id,
        ref=ref,
        amount_minor=amount_minor,
        currency=currency,
        occurred_at=occurred_at,
        payer=target.support_seeker,
        payee=target.meeting.peer,
        provider_object_id=provider_object_id,
        base_amount_minor=int(base_amount * 100),
        base_currency=base_currency,
        exchange_rate=rate,
    )
    record_activity(
        event_type="booking_paid",
        object_type=object_type,
        object_id=target.pk,
        occurred_at=occurred_at,
    )


def _checkout_fee_minor(payment_intent, amount_total):
    from neuromancers_network.analytics.services import configured_fee_minor  # noqa: PLC0415

    if payment_intent is not None:
        fee = payment_intent.get("application_fee_amount")
        if fee is not None:
            return fee
    return configured_fee_minor(amount_total or 0)


def _record_session_fee(*, provider_key, fee_minor, currency, occurred_at):
    from neuromancers_network.analytics.services import record_application_fee  # noqa: PLC0415

    if not fee_minor:
        return
    record_application_fee(
        provider_key=provider_key,
        fee_minor=fee_minor,
        currency=currency,
        occurred_at=occurred_at,
    )


@djstripe_receiver("checkout.session.completed")
def handle_checkout_session_completed(sender, event, **kwargs):
    """Mark a meeting request or booking paid when Stripe Checkout completes."""
    from neuromancers_network.analytics.services import occurred_at_from  # noqa: PLC0415
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    session_data = event.data.get("object", {})
    session_id = session_data.get("id")
    payment_intent_id = session_data.get("payment_intent")
    amount_total = session_data.get("amount_total")
    payment_intent = None

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

    occurred_at = occurred_at_from(session_data)
    fee_minor = _checkout_fee_minor(payment_intent, amount_total)
    currency = session_data.get("currency")
    currency_conversion = (
        payment_intent.get("currency_conversion")
        if payment_intent is not None
        else None
    )
    fee_key = payment_intent_id or session_id

    meeting_request = MeetingRequest.objects.filter(
        stripe_checkout_session_id=session_id,
    ).first()
    if meeting_request is not None:
        meeting_request.sync_payment_from_checkout(
            session_id,
            payment_intent_id,
            amount_total,
            currency_conversion=currency_conversion,
        )
        _record_item_ledger(
            session_id=session_id,
            ref=f"request:{meeting_request.pk}",
            amount_minor=amount_total,
            currency=currency,
            occurred_at=occurred_at,
            provider_object_id=payment_intent_id or "",
            currency_conversion=currency_conversion,
        )
        _record_session_fee(
            provider_key=fee_key,
            fee_minor=fee_minor,
            currency=currency,
            occurred_at=occurred_at,
        )
        return

    booking = Booking.objects.filter(stripe_checkout_session_id=session_id).first()
    if booking is not None:
        refs = _line_item_refs(session_data)
        if refs:
            _apply_line_item_amounts(
                session_id,
                session_data,
                refs,
                event,
                currency_conversion=currency_conversion,
            )
            _record_session_fee(
                provider_key=fee_key,
                fee_minor=fee_minor,
                currency=currency,
                occurred_at=occurred_at,
            )
            return
        # Legacy sessions created before per-item refs: mark the booking only.
        if payment_intent_id and booking.stripe_payment_intent_id != payment_intent_id:
            booking.stripe_payment_intent_id = payment_intent_id
        if can_proceed(booking.mark_paid):
            booking.mark_paid()
        booking.save()
        booking.record_receipt()
        _record_item_ledger(
            session_id=session_id,
            ref=f"booking:{booking.pk}",
            amount_minor=amount_total,
            currency=currency,
            occurred_at=occurred_at,
            provider_object_id=payment_intent_id or "",
            currency_conversion=currency_conversion,
        )
        _record_session_fee(
            provider_key=fee_key,
            fee_minor=fee_minor,
            currency=currency,
            occurred_at=occurred_at,
        )


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


def _apply_line_item_amounts(
    session_id,
    session_data,
    refs,
    event,
    currency_conversion=None,
) -> None:
    """Apply each Stripe line item amount to its referenced record."""
    from neuromancers_network.analytics.services import occurred_at_from  # noqa: PLC0415
    from neuromancers_network.payments.services import receipt_url_for  # noqa: PLC0415

    occurred_at = occurred_at_from(session_data)
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
        _record_item_ledger(
            session_id=session_id,
            ref=ref,
            amount_minor=amount_total,
            currency=getattr(item, "currency", None) or session_data.get("currency"),
            occurred_at=occurred_at,
            provider_object_id=getattr(item, "id", ""),
            currency_conversion=currency_conversion,
        )

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
    """Mark a local refund request as refunded and record the refund value."""
    from neuromancers_network.analytics.services import occurred_at_from  # noqa: PLC0415
    from neuromancers_network.analytics.services import record_activity  # noqa: PLC0415
    from neuromancers_network.analytics.services import record_refund  # noqa: PLC0415
    from neuromancers_network.meetings.models import RefundRequest  # noqa: PLC0415

    charge_data = event.data.get("object", {})
    refunds = charge_data.get("refunds", {}).get("data", [])

    if not refunds:
        logger.warning("Ignoring charge.refunded without refund data")
        return

    fallback_payer, fallback_payee = _participants_for_payment_intent(
        charge_data.get("payment_intent"),
    )
    for refund_data in refunds:
        refund_id = refund_data.get("id")
        if not refund_id:
            continue

        sync_from_event(StripeRefund, refund_data, event)

        refund_request = (
            RefundRequest.objects.filter(stripe_refund_id=refund_id)
            .select_related(
                "meeting_request__meeting",
                "meeting_request__support_seeker",
            )
            .first()
        )
        if refund_request is not None:
            payer = refund_request.meeting_request.support_seeker
            payee = refund_request.meeting_request.meeting.peer
            if can_proceed(refund_request.mark_refunded):
                refund_request.mark_refunded()
                refund_request.save(update_fields=["status", "updated_at"])
        else:
            payer, payee = fallback_payer, fallback_payee

        occurred_at = occurred_at_from(refund_data)
        record_refund(
            refund_id=refund_id,
            amount_minor=refund_data.get("amount"),
            currency=refund_data.get("currency") or charge_data.get("currency"),
            occurred_at=occurred_at,
            payer=payer,
            payee=payee,
        )
        record_activity(
            event_type="refund",
            object_type="refund",
            object_id=refund_id,
            occurred_at=occurred_at,
        )


@djstripe_receiver(["charge.dispute.created", "charge.dispute.closed"])
def handle_charge_dispute(sender, event, **kwargs):
    """Sync the dispute and record it on the marketplace ledger."""
    from neuromancers_network.analytics.services import occurred_at_from  # noqa: PLC0415
    from neuromancers_network.analytics.services import record_activity  # noqa: PLC0415
    from neuromancers_network.analytics.services import record_dispute  # noqa: PLC0415

    dispute_data = event.data.get("object", {})
    dispute_id = dispute_data.get("id")
    if not dispute_id:
        logger.warning("Ignoring %s without dispute id", event.type)
        return
    sync_from_event(StripeDispute, dispute_data, event)

    payer, payee = _participants_for_payment_intent(
        dispute_data.get("payment_intent"),
    )
    occurred_at = occurred_at_from(dispute_data)
    record_dispute(
        dispute_id=dispute_id,
        amount_minor=dispute_data.get("amount"),
        currency=dispute_data.get("currency"),
        occurred_at=occurred_at,
        payer=payer,
        payee=payee,
    )
    record_activity(
        event_type="dispute",
        object_type="dispute",
        object_id=dispute_id,
        occurred_at=occurred_at,
    )
