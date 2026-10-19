"""Pure metric definitions over the analytics ledgers.

Periods are UTC calendar months; ``now`` is injectable so results are
deterministic in tests. Amounts are major units and converted with the ledger's
persisted exchange rate when present.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal

from django.db.models import Count
from django.db.models import Q
from django.db.models import Sum
from django.utils import timezone

from neuromancers_network.analytics.models import SessionLedger
from neuromancers_network.analytics.models import SubscriptionKind
from neuromancers_network.analytics.models import SubscriptionLedger
from neuromancers_network.analytics.models import TransactionKind
from neuromancers_network.analytics.models import TransactionLedger
from neuromancers_network.core.currency import convert_amount

PERIOD_ALL_TIME = "all_time"
PERIOD_THIS_MONTH = "this_month"
PERIOD_LAST_MONTH = "last_month"
PERIOD_LAST_3_MONTHS = "last_3_months"
PERIODS = (
    PERIOD_ALL_TIME,
    PERIOD_THIS_MONTH,
    PERIOD_LAST_MONTH,
    PERIOD_LAST_3_MONTHS,
)

MONEY = Decimal("0.01")
REPEAT_BOOKING_THRESHOLD = 2


def _quantize(value) -> Decimal:
    return Decimal(value or 0).quantize(MONEY)


def _month_start(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def add_months(value: datetime, months: int) -> datetime:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return value.replace(year=year, month=month, day=1)


def period_bounds(period: str, now: datetime | None = None):
    """Return ``(start, end)`` for a period; ``start`` is ``None`` for all time."""
    now = now or timezone.now()
    if period == PERIOD_ALL_TIME:
        return None, now
    start = _month_start(now)
    if period == PERIOD_THIS_MONTH:
        return start, now
    if period == PERIOD_LAST_MONTH:
        return add_months(start, -1), start
    if period == PERIOD_LAST_3_MONTHS:
        return add_months(start, -2), now
    message = f"Unknown analytics period {period!r}"
    raise ValueError(message)


def _in_period(queryset, start, end, *, field="occurred_at"):
    if start is None:
        return queryset
    return queryset.filter(**{f"{field}__gte": start, f"{field}__lt": end})


def transactions(*, period, user=None, role="all", now=None):
    """Ledger rows for a period, optionally scoped to a payer/payee."""
    start, end = period_bounds(period, now)
    queryset = _in_period(TransactionLedger.objects.all(), start, end)
    if user is None:
        return queryset
    if role == "payer":
        return queryset.filter(payer=user)
    if role == "payee":
        return queryset.filter(payee=user)
    return queryset.filter(Q(payer=user) | Q(payee=user))


def amounts_by_currency(queryset) -> dict[str, Decimal]:
    """Per-currency totals (a refund row is already negative)."""
    rows = (
        queryset.values("presentment_currency")
        .annotate(total=Sum("presentment_amount"))
        .order_by("presentment_currency")
    )
    return {row["presentment_currency"]: _quantize(row["total"]) for row in rows}


def converted_total(queryset, target_currency: str | None = None) -> Decimal:
    """Sum rows in *target_currency*, using each row's persisted rate."""
    total = Decimal("0")
    for entry in queryset.iterator():
        total += convert_amount(
            entry.presentment_amount,
            source_currency=entry.presentment_currency,
            target_currency=target_currency,
            rate=entry.exchange_rate,
        )
    return _quantize(total)


def _sum_kind(queryset, kind) -> Decimal:
    return _quantize(
        queryset.filter(kind=kind).aggregate(total=Sum("presentment_amount"))["total"],
    )


def gbv(queryset) -> Decimal:
    """Gross booking value: positive booking-payment amounts."""
    return _sum_kind(queryset, TransactionKind.BOOKING_PAYMENT)


def application_fees(queryset) -> Decimal:
    return _sum_kind(queryset, TransactionKind.APPLICATION_FEE)


def refunds(queryset) -> Decimal:
    """Refunded value as a positive amount (rows are negative)."""
    return abs(_sum_kind(queryset, TransactionKind.REFUND))


def disputes(queryset) -> Decimal:
    return abs(_sum_kind(queryset, TransactionKind.DISPUTE))


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if not denominator:
        return Decimal("0")
    return (numerator / denominator).quantize(Decimal("0.0001"))


def take_rate(queryset) -> Decimal:
    return _ratio(application_fees(queryset), gbv(queryset))


def refund_rate(queryset) -> Decimal:
    return _ratio(refunds(queryset), gbv(queryset))


def average_order_value(queryset) -> Decimal:
    payments = queryset.filter(kind=TransactionKind.BOOKING_PAYMENT)
    count = payments.count()
    if not count:
        return Decimal("0.00")
    return (gbv(queryset) / Decimal(count)).quantize(MONEY)


def active_members(queryset) -> int:
    return (
        queryset.filter(
            kind=TransactionKind.BOOKING_PAYMENT,
            payer__isnull=False,
        )
        .values_list("payer_id", flat=True)
        .distinct()
        .count()
    )


def active_peers(queryset) -> int:
    return (
        queryset.filter(
            kind=TransactionKind.BOOKING_PAYMENT,
            payee__isnull=False,
        )
        .values_list("payee_id", flat=True)
        .distinct()
        .count()
    )


def repeat_booking_rate(queryset) -> Decimal:
    """Seekers with at least two payments, over seekers with one or more."""
    per_seeker = (
        queryset.filter(
            kind=TransactionKind.BOOKING_PAYMENT,
            payer__isnull=False,
        )
        .values("payer_id")
        .annotate(total=Count("id"))
    )
    seekers = list(per_seeker)
    if not seekers:
        return Decimal("0")
    repeat = sum(1 for row in seekers if row["total"] >= REPEAT_BOOKING_THRESHOLD)
    return _ratio(Decimal(repeat), Decimal(len(seekers)))


def session_minutes(*, period, now=None) -> dict[str, int]:
    start, end = period_bounds(period, now)
    queryset = _in_period(SessionLedger.objects.all(), start, end)
    rows = (
        queryset.values("provider").annotate(total=Sum("minutes")).order_by("provider")
    )
    return {row["provider"] or "unknown": row["total"] or 0 for row in rows}


def subscription_revenue(*, period, now=None) -> Decimal:
    start, end = period_bounds(period, now)
    queryset = _in_period(
        SubscriptionLedger.objects.filter(kind=SubscriptionKind.PAYMENT),
        start,
        end,
    )
    return _quantize(queryset.aggregate(total=Sum("presentment_amount"))["total"])


def _status_counts(model, *, period, now=None) -> dict[str, int]:
    start, end = period_bounds(period, now)
    queryset = _in_period(model.objects.all(), start, end, field="created_at")
    rows = queryset.values("status").annotate(total=Count("id")).order_by("status")
    return {row["status"]: row["total"] for row in rows}


def requests_by_status(*, period, now=None) -> dict[str, int]:
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    return _status_counts(MeetingRequest, period=period, now=now)


def bookings_by_status(*, period, now=None) -> dict[str, int]:
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415

    return _status_counts(Booking, period=period, now=now)


def published_review_rate(*, period, now=None) -> Decimal:
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415
    from neuromancers_network.meetings.models import (  # noqa: PLC0415
        MeetingRequestStatus,
    )
    from neuromancers_network.meetings.models import Review  # noqa: PLC0415

    start, end = period_bounds(period, now)
    reviews = _in_period(
        Review.objects.filter(is_published=True),
        start,
        end,
        field="created_at",
    ).count()
    completed = _in_period(
        MeetingRequest.objects.filter(status=MeetingRequestStatus.COMPLETED),
        start,
        end,
        field="created_at",
    ).count()
    return _ratio(Decimal(reviews), Decimal(completed))


def platform_metrics(*, period, now=None, target_currency=None) -> dict:
    """Platform-scope metrics for a period."""
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingStatus  # noqa: PLC0415
    from neuromancers_network.peers.models import PeerProfile  # noqa: PLC0415

    queryset = transactions(period=period, now=now)
    payments = queryset.filter(kind=TransactionKind.BOOKING_PAYMENT)
    return {
        "period": period,
        "transactions": queryset.count(),
        "payments": payments.count(),
        "gbv": gbv(queryset),
        "gbv_by_currency": amounts_by_currency(payments),
        "gbv_converted": converted_total(payments, target_currency),
        "application_fees": application_fees(queryset),
        "take_rate": take_rate(queryset),
        "refunds": refunds(queryset),
        "refund_rate": refund_rate(queryset),
        "disputes": disputes(queryset),
        "average_order_value": average_order_value(queryset),
        "subscription_revenue": subscription_revenue(period=period, now=now),
        "session_minutes": session_minutes(period=period, now=now),
        "active_members": active_members(queryset),
        "active_peers": active_peers(queryset),
        "repeat_booking_rate": repeat_booking_rate(queryset),
        "published_review_rate": published_review_rate(period=period, now=now),
        "requests_by_status": requests_by_status(period=period, now=now),
        "bookings_by_status": bookings_by_status(period=period, now=now),
        "users": get_user_model().objects.filter(is_active=True).count(),
        "peers": PeerProfile.objects.filter(is_approved=True).count(),
        "meetings": Meeting.objects.filter(status=MeetingStatus.PUBLISHED).count(),
    }


def peer_metrics(peer, *, period, now=None, target_currency=None) -> dict:
    """Peer-scope metrics (marketplace money received by *peer*)."""
    queryset = transactions(period=period, user=peer, role="payee", now=now)
    payments = queryset.filter(kind=TransactionKind.BOOKING_PAYMENT)
    return {
        "period": period,
        "payments": payments.count(),
        "gbv": gbv(queryset),
        "gbv_by_currency": amounts_by_currency(payments),
        "gbv_converted": converted_total(payments, target_currency),
        "application_fees": application_fees(queryset),
        "take_rate": take_rate(queryset),
        "refunds": refunds(queryset),
        "refund_rate": refund_rate(queryset),
        "average_order_value": average_order_value(queryset),
    }


def member_metrics(member, *, period, now=None, target_currency=None) -> dict:
    """Member-scope metrics (marketplace money paid by *member*)."""
    queryset = transactions(period=period, user=member, role="payer", now=now)
    payments = queryset.filter(kind=TransactionKind.BOOKING_PAYMENT)
    return {
        "period": period,
        "payments": payments.count(),
        "spend": gbv(queryset),
        "spend_by_currency": amounts_by_currency(payments),
        "spend_converted": converted_total(payments, target_currency),
        "refunds": refunds(queryset),
    }
