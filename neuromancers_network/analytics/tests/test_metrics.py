from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal

import pytest

from neuromancers_network.analytics.metrics import PERIOD_ALL_TIME
from neuromancers_network.analytics.metrics import PERIOD_LAST_3_MONTHS
from neuromancers_network.analytics.metrics import PERIOD_LAST_MONTH
from neuromancers_network.analytics.metrics import PERIOD_THIS_MONTH
from neuromancers_network.analytics.metrics import gbv
from neuromancers_network.analytics.metrics import member_metrics
from neuromancers_network.analytics.metrics import peer_metrics
from neuromancers_network.analytics.metrics import period_bounds
from neuromancers_network.analytics.metrics import platform_metrics
from neuromancers_network.analytics.metrics import session_minutes
from neuromancers_network.analytics.metrics import transactions
from neuromancers_network.analytics.models import TransactionKind
from neuromancers_network.analytics.models import TransactionLedger
from neuromancers_network.analytics.services import record_application_fee
from neuromancers_network.analytics.services import record_payment
from neuromancers_network.analytics.services import record_refund
from neuromancers_network.analytics.services import record_session
from neuromancers_network.analytics.services import record_subscription_payment
from neuromancers_network.analytics.services import record_transaction
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
OCCURRED = datetime(2026, 5, 10, 9, 0, tzinfo=UTC)
EXPECTED_PAYMENTS = 3
EXPECTED_ACTORS = 2
EXPECTED_SCOPED_PAYMENTS = 2


class TestPeriodBounds:
    def test_this_month(self):
        start, end = period_bounds(PERIOD_THIS_MONTH, NOW)

        assert start == datetime(2026, 5, 1, tzinfo=UTC)
        assert end == NOW

    def test_last_month(self):
        start, end = period_bounds(PERIOD_LAST_MONTH, NOW)

        assert start == datetime(2026, 4, 1, tzinfo=UTC)
        assert end == datetime(2026, 5, 1, tzinfo=UTC)

    def test_last_three_months(self):
        start, _end = period_bounds(PERIOD_LAST_3_MONTHS, NOW)

        assert start == datetime(2026, 3, 1, tzinfo=UTC)

    def test_all_time(self):
        start, end = period_bounds(PERIOD_ALL_TIME, NOW)

        assert start is None
        assert end == NOW

    def test_unknown_period_raises(self):
        with pytest.raises(ValueError, match="Unknown analytics period"):
            period_bounds("fortnight", NOW)


def _seed_ledgers():
    first = UserFactory()
    second = UserFactory()
    peer = make_peer()
    other_peer = make_peer()

    record_payment(
        session_id="cs_1",
        ref="request:1",
        amount_minor=2500,
        currency="GBP",
        occurred_at=OCCURRED,
        payer=first,
        payee=peer,
    )
    record_payment(
        session_id="cs_2",
        ref="request:2",
        amount_minor=5000,
        currency="GBP",
        occurred_at=OCCURRED,
        payer=first,
        payee=peer,
    )
    record_payment(
        session_id="cs_3",
        ref="request:3",
        amount_minor=1000,
        currency="GBP",
        occurred_at=OCCURRED,
        payer=second,
        payee=other_peer,
    )
    record_application_fee(
        provider_key="pi_1",
        fee_minor=1500,
        currency="GBP",
        occurred_at=OCCURRED,
    )
    record_refund(
        refund_id="re_1",
        amount_minor=1000,
        currency="GBP",
        occurred_at=OCCURRED,
    )
    return first, second, peer, other_peer


class TestPlatformMetrics:
    def test_totals_rates_and_activity(self):
        _seed_ledgers()

        metrics = platform_metrics(period=PERIOD_THIS_MONTH, now=NOW)

        assert metrics["payments"] == EXPECTED_PAYMENTS
        assert metrics["gbv"] == Decimal("85.00")
        assert metrics["application_fees"] == Decimal("15.00")
        assert metrics["take_rate"] == Decimal("0.1765")
        assert metrics["refunds"] == Decimal("10.00")
        assert metrics["refund_rate"] == Decimal("0.1176")
        assert metrics["average_order_value"] == Decimal("28.33")
        assert metrics["active_members"] == EXPECTED_ACTORS
        assert metrics["active_peers"] == EXPECTED_ACTORS
        assert metrics["repeat_booking_rate"] == Decimal("0.5000")
        assert metrics["gbv_by_currency"] == {"GBP": Decimal("85.00")}

    def test_period_excludes_other_months(self):
        _seed_ledgers()
        record_payment(
            session_id="cs_old",
            ref="request:9",
            amount_minor=9900,
            currency="GBP",
            occurred_at=datetime(2026, 1, 5, tzinfo=UTC),
            payer=UserFactory(),
            payee=make_peer(),
        )

        metrics = platform_metrics(period=PERIOD_THIS_MONTH, now=NOW)

        assert metrics["gbv"] == Decimal("85.00")

    def test_converted_total_uses_the_persisted_rate(self):
        _seed_ledgers()
        TransactionLedger.objects.filter(
            kind=TransactionKind.BOOKING_PAYMENT,
        ).update(exchange_rate=Decimal("1.2"))

        metrics = platform_metrics(
            period=PERIOD_THIS_MONTH,
            now=NOW,
            target_currency="EUR",
        )

        assert metrics["gbv_converted"] == Decimal("102.00")

    def test_session_minutes_and_subscription_revenue(self):
        peer = make_peer()
        request_row = MeetingRequest.objects.create(
            meeting=create_meeting(peer=peer),
            support_seeker=UserFactory(),
            status=MeetingRequestStatus.PAID,
        )
        record_session(
            meeting_request=request_row,
            minutes=45,
            provider="whereby",
            occurred_at=OCCURRED,
        )
        record_subscription_payment(
            invoice_id="in_1",
            subscription_id="sub_1",
            amount_minor=999,
            currency="GBP",
            occurred_at=OCCURRED,
        )

        metrics = platform_metrics(period=PERIOD_THIS_MONTH, now=NOW)

        assert session_minutes(period=PERIOD_THIS_MONTH, now=NOW) == {
            "whereby": 45,
        }
        assert metrics["subscription_revenue"] == Decimal("9.99")


class TestScopedMetrics:
    def test_peer_and_member_scopes(self):
        first, _second, peer, _other = _seed_ledgers()

        peer_view = peer_metrics(peer, period=PERIOD_THIS_MONTH, now=NOW)
        member_view = member_metrics(first, period=PERIOD_THIS_MONTH, now=NOW)

        assert peer_view["gbv"] == Decimal("75.00")
        assert peer_view["payments"] == EXPECTED_SCOPED_PAYMENTS
        assert member_view["spend"] == Decimal("75.00")
        assert member_view["payments"] == EXPECTED_SCOPED_PAYMENTS

    def test_gbv_helper_ignores_fees_and_refunds(self):
        _seed_ledgers()

        queryset = transactions(period=PERIOD_THIS_MONTH, now=NOW)

        assert gbv(queryset) == Decimal("85.00")


class TestDeterminism:
    def test_same_inputs_same_outputs(self):
        _seed_ledgers()

        first = platform_metrics(period=PERIOD_THIS_MONTH, now=NOW)
        second = platform_metrics(period=PERIOD_THIS_MONTH, now=NOW)

        assert first == second

    def test_transaction_without_rate_is_still_valid(self):
        user = UserFactory()
        record_transaction(
            kind=TransactionKind.BOOKING_PAYMENT,
            idempotency_key="manual:1",
            amount_minor=1000,
            currency="GBP",
            occurred_at=OCCURRED,
            payer=user,
        )

        assert TransactionLedger.objects.filter(idempotency_key="manual:1").exists()
