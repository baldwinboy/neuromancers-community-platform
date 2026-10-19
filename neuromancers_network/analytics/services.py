"""Idempotent ledger writers and backfill for analytics."""

from __future__ import annotations

import logging
from datetime import UTC
from datetime import datetime
from decimal import ROUND_HALF_UP
from decimal import Decimal

from django.utils import timezone

from neuromancers_network.analytics.models import ActivityLedger
from neuromancers_network.analytics.models import SessionLedger
from neuromancers_network.analytics.models import SubscriptionKind
from neuromancers_network.analytics.models import SubscriptionLedger
from neuromancers_network.analytics.models import TransactionKind
from neuromancers_network.analytics.models import TransactionLedger

logger = logging.getLogger(__name__)

MONEY = Decimal("0.01")


def _major(minor) -> Decimal:
    return (Decimal(minor or 0) / 100).quantize(MONEY)


def occurred_at_from(data, fallback=None):
    """Return the provider's creation time when present (replay-stable)."""
    created = data.get("created") if isinstance(data, dict) else None
    if created:
        return datetime.fromtimestamp(int(created), tz=UTC)
    return fallback or timezone.now()


def _currency(value, fallback="GBP") -> str:
    return (value or fallback).upper()


def record_transaction(  # noqa: PLR0913
    *,
    kind,
    idempotency_key,
    amount_minor,
    currency,
    occurred_at,
    payer=None,
    payee=None,
    fee_minor=0,
    provider_object_id="",
    exchange_rate=None,
) -> TransactionLedger:
    """Upsert one marketplace ledger row keyed by *idempotency_key*."""
    amount = _major(amount_minor)
    fee = _major(fee_minor)
    net = amount - fee if kind == TransactionKind.BOOKING_PAYMENT else amount
    entry, _created = TransactionLedger.objects.update_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "kind": kind,
            "base_currency": _currency(currency),
            "base_amount": amount,
            "presentment_currency": _currency(currency),
            "presentment_amount": amount,
            "exchange_rate": exchange_rate,
            "fee_amount": fee,
            "net_amount": net,
            "payer": payer,
            "payee": payee,
            "provider_object_id": provider_object_id,
            "occurred_at": occurred_at,
        },
    )
    return entry


def record_payment(  # noqa: PLR0913
    *,
    session_id,
    ref,
    amount_minor,
    currency,
    occurred_at,
    payer=None,
    payee=None,
    provider_object_id="",
) -> TransactionLedger:
    return record_transaction(
        kind=TransactionKind.BOOKING_PAYMENT,
        idempotency_key=f"payment:{session_id}:{ref}",
        amount_minor=amount_minor,
        currency=currency,
        occurred_at=occurred_at,
        payer=payer,
        payee=payee,
        provider_object_id=provider_object_id,
    )


def configured_fee_minor(amount_minor) -> int:
    from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415

    percent = Decimal(StripeSettings.load().application_fee or 0)
    return int(
        (Decimal(amount_minor or 0) * percent / Decimal(100)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        ),
    )


def record_application_fee(  # noqa: PLR0913
    *,
    provider_key,
    fee_minor,
    currency,
    occurred_at,
    payer=None,
    payee=None,
    provider_object_id="",
) -> TransactionLedger:
    return record_transaction(
        kind=TransactionKind.APPLICATION_FEE,
        idempotency_key=f"fee:{provider_key}",
        amount_minor=fee_minor,
        currency=currency,
        occurred_at=occurred_at,
        payer=payer,
        payee=payee,
        provider_object_id=provider_object_id,
    )


def record_refund(  # noqa: PLR0913
    *,
    refund_id,
    amount_minor,
    currency,
    occurred_at,
    payer=None,
    payee=None,
    provider_object_id="",
) -> TransactionLedger:
    return record_transaction(
        kind=TransactionKind.REFUND,
        idempotency_key=f"refund:{refund_id}",
        amount_minor=-abs(int(amount_minor or 0)),
        currency=currency,
        occurred_at=occurred_at,
        payer=payer,
        payee=payee,
        provider_object_id=provider_object_id or refund_id,
    )


def record_dispute(  # noqa: PLR0913
    *,
    dispute_id,
    amount_minor,
    currency,
    occurred_at,
    payer=None,
    payee=None,
    provider_object_id="",
) -> TransactionLedger:
    return record_transaction(
        kind=TransactionKind.DISPUTE,
        idempotency_key=f"dispute:{dispute_id}",
        amount_minor=-abs(int(amount_minor or 0)),
        currency=currency,
        occurred_at=occurred_at,
        payer=payer,
        payee=payee,
        provider_object_id=provider_object_id or dispute_id,
    )


def record_subscription_payment(  # noqa: PLR0913
    *,
    invoice_id,
    subscription_id,
    amount_minor,
    currency,
    occurred_at,
    payer=None,
) -> SubscriptionLedger:
    amount = _major(amount_minor)
    entry, _created = SubscriptionLedger.objects.update_or_create(
        idempotency_key=f"invoice:{invoice_id}",
        defaults={
            "kind": SubscriptionKind.PAYMENT,
            "invoice_id": invoice_id,
            "subscription_id": subscription_id or "",
            "payer": payer,
            "base_currency": _currency(currency),
            "base_amount": amount,
            "presentment_currency": _currency(currency),
            "presentment_amount": amount,
            "occurred_at": occurred_at,
        },
    )
    return entry


def record_session(
    *,
    meeting_request,
    minutes,
    provider="",
    occurred_at=None,
) -> SessionLedger:
    meeting = meeting_request.meeting
    entry, _created = SessionLedger.objects.update_or_create(
        meeting_request=meeting_request,
        defaults={
            "provider": provider,
            "minutes": max(0, int(minutes or 0)),
            "peer": meeting.peer,
            "seeker": meeting_request.support_seeker,
            "occurred_at": occurred_at or timezone.now(),
        },
    )
    return entry


def record_activity(*, event_type, object_type, object_id, occurred_at=None):
    entry, _created = ActivityLedger.objects.update_or_create(
        idempotency_key=f"activity:{event_type}:{object_type}:{object_id}",
        defaults={
            "event_type": event_type,
            "object_type": object_type,
            "object_id": str(object_id),
            "occurred_at": occurred_at or timezone.now(),
        },
    )
    return entry


def sync_analytics_ledgers() -> dict[str, int]:
    """Backfill ledgers from local records (idempotent)."""
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415
    from neuromancers_network.meetings.models import RefundRequest  # noqa: PLC0415
    from neuromancers_network.meetings.models import RefundStatus  # noqa: PLC0415

    counts = {"payments": 0, "refunds": 0}

    requests = MeetingRequest.objects.filter(
        price_paid__isnull=False,
        price_paid__gt=0,
    ).select_related("meeting")
    for request_row in requests.iterator():
        session_id = (
            request_row.stripe_checkout_session_id or f"request-{request_row.pk}"
        )
        record_payment(
            session_id=session_id,
            ref=f"request:{request_row.pk}",
            amount_minor=int(request_row.price_paid * 100),
            currency=request_row.meeting.currency,
            occurred_at=request_row.updated_at,
            payer=request_row.support_seeker,
            payee=request_row.meeting.peer,
            provider_object_id=request_row.stripe_payment_intent_id,
        )
        counts["payments"] += 1

    sessionless = Booking.objects.filter(
        total_amount__isnull=False,
        total_amount__gt=0,
        sessions__isnull=True,
    ).select_related("meeting")
    for booking in sessionless.iterator():
        session_id = booking.stripe_checkout_session_id or f"booking-{booking.pk}"
        record_payment(
            session_id=session_id,
            ref=f"booking:{booking.pk}",
            amount_minor=int(booking.total_amount * 100),
            currency=booking.currency,
            occurred_at=booking.updated_at,
            payer=booking.support_seeker,
            payee=booking.meeting.peer,
            provider_object_id=booking.stripe_payment_intent_id,
        )
        counts["payments"] += 1

    refunds = RefundRequest.objects.filter(
        status=RefundStatus.REFUNDED,
        stripe_refund_id__gt="",
    ).select_related("meeting_request__meeting", "meeting_request__support_seeker")
    for refund in refunds.iterator():
        request_row = refund.meeting_request
        amount_minor = int((request_row.price_paid or Decimal("0")) * 100)
        if not amount_minor:
            continue
        record_refund(
            refund_id=refund.stripe_refund_id,
            amount_minor=amount_minor,
            currency=request_row.meeting.currency,
            occurred_at=refund.updated_at,
            payer=request_row.support_seeker,
            payee=request_row.meeting.peer,
        )
        counts["refunds"] += 1

    return counts
