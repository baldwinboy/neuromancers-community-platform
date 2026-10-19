from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal

import pytest

from neuromancers_network.analytics.models import ActivityLedger
from neuromancers_network.analytics.models import SessionLedger
from neuromancers_network.analytics.models import SubscriptionLedger
from neuromancers_network.analytics.models import TransactionKind
from neuromancers_network.analytics.models import TransactionLedger
from neuromancers_network.analytics.services import configured_fee_minor
from neuromancers_network.analytics.services import occurred_at_from
from neuromancers_network.analytics.services import record_activity
from neuromancers_network.analytics.services import record_payment
from neuromancers_network.analytics.services import record_refund
from neuromancers_network.analytics.services import record_session
from neuromancers_network.analytics.services import record_subscription_payment
from neuromancers_network.analytics.services import sync_analytics_ledgers
from neuromancers_network.core.models import StripeSettings
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import RefundRequest
from neuromancers_network.meetings.models import RefundStatus
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

OCCURRED = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
EXPECTED_FEE_MINOR = 1500
SESSION_MINUTES = 60


class TestPaymentLedger:
    def test_replay_creates_one_row_with_net_amount(self):
        payer = UserFactory()
        payee = UserFactory()

        first = record_payment(
            session_id="cs_1",
            ref="request:10",
            amount_minor=2500,
            currency="gbp",
            occurred_at=OCCURRED,
            payer=payer,
            payee=payee,
        )
        second = record_payment(
            session_id="cs_1",
            ref="request:10",
            amount_minor=2500,
            currency="gbp",
            occurred_at=OCCURRED,
            payer=payer,
            payee=payee,
        )

        assert first.pk == second.pk
        assert TransactionLedger.objects.count() == 1
        assert first.kind == TransactionKind.BOOKING_PAYMENT
        assert first.presentment_amount == Decimal("25.00")
        assert first.presentment_currency == "GBP"
        assert first.net_amount == Decimal("25.00")

    def test_configured_fee_uses_the_percentage(self):
        config = StripeSettings.load()
        config.application_fee = 15
        config.save()

        assert configured_fee_minor(10_000) == EXPECTED_FEE_MINOR


class TestRefundLedger:
    def test_refund_is_negative_and_replay_safe(self):
        record_refund(
            refund_id="re_1",
            amount_minor=1000,
            currency="gbp",
            occurred_at=OCCURRED,
        )
        record_refund(
            refund_id="re_1",
            amount_minor=1000,
            currency="gbp",
            occurred_at=OCCURRED,
        )

        entry = TransactionLedger.objects.get()
        assert entry.kind == TransactionKind.REFUND
        assert entry.presentment_amount == Decimal("-10.00")
        assert entry.net_amount == Decimal("-10.00")


class TestSubscriptionLedger:
    def test_invoice_replay_is_idempotent(self):
        record_subscription_payment(
            invoice_id="in_1",
            subscription_id="sub_1",
            amount_minor=999,
            currency="gbp",
            occurred_at=OCCURRED,
        )
        record_subscription_payment(
            invoice_id="in_1",
            subscription_id="sub_1",
            amount_minor=999,
            currency="gbp",
            occurred_at=OCCURRED,
        )

        entry = SubscriptionLedger.objects.get()
        assert entry.presentment_amount == Decimal("9.99")


class TestSessionLedger:
    def test_session_replay_is_idempotent(self):
        peer = make_peer()
        request_row = MeetingRequest.objects.create(
            meeting=create_meeting(peer=peer),
            support_seeker=UserFactory(),
            status=MeetingRequestStatus.PAID,
        )

        record_session(
            meeting_request=request_row,
            minutes=60,
            provider="whereby",
            occurred_at=OCCURRED,
        )
        record_session(
            meeting_request=request_row,
            minutes=60,
            provider="whereby",
            occurred_at=OCCURRED,
        )

        entry = SessionLedger.objects.get()
        assert entry.minutes == SESSION_MINUTES
        assert entry.provider == "whereby"


class TestActivityLedger:
    def test_activity_replay_is_idempotent(self):
        record_activity(
            event_type="booking_paid",
            object_type="booking",
            object_id=5,
            occurred_at=OCCURRED,
        )
        record_activity(
            event_type="booking_paid",
            object_type="booking",
            object_id=5,
            occurred_at=OCCURRED,
        )

        assert ActivityLedger.objects.count() == 1


class TestBackfill:
    def test_backfill_is_idempotent(self):
        peer = make_peer()
        request_row = MeetingRequest.objects.create(
            meeting=create_meeting(peer=peer),
            support_seeker=UserFactory(),
            status=MeetingRequestStatus.PAID,
            price_paid=Decimal("25.00"),
            stripe_checkout_session_id="cs_backfill",
        )
        RefundRequest.objects.create(
            meeting_request=request_row,
            reason="test",
            status=RefundStatus.REFUNDED,
            stripe_refund_id="re_backfill",
        )

        first = sync_analytics_ledgers()
        second = sync_analytics_ledgers()

        assert first == second
        assert TransactionLedger.objects.filter(
            kind=TransactionKind.BOOKING_PAYMENT,
        ).exists()
        assert TransactionLedger.objects.filter(kind=TransactionKind.REFUND).exists()


class TestOccurredAt:
    def test_uses_the_provider_timestamp(self):
        result = occurred_at_from({"created": 1_700_000_000})

        assert result == datetime.fromtimestamp(1_700_000_000, tz=UTC)
