from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import BookingStatus
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingPriceOption
from neuromancers_network.meetings.models import MeetingPriceTier
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.models import RefundStatus
from neuromancers_network.meetings.selectors import user_payment_history
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import AccountFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PUBLISHABLE_KEY = "pk_test_123"
SECRET_KEY = "sk_test_123"  # noqa: S105
PEER_ACCOUNT_ID = "acct_peer"
CONNECT_ACCOUNT_ID = "acct_refund"
BOOKING_TOTAL = Decimal("20.00")
APPLICATION_FEE_PERCENT = 10
SESSION_DURATION = 30
TIER_PRICE = Decimal("15.00")
PAID_TOTAL = Decimal("10.00")
EXPECTED_PARTIAL_REFUND_MINOR = 500


def configure_stripe(
    *,
    application_fee=APPLICATION_FEE_PERCENT,
    allow_partial_refunds=False,
    charge_type=StripeSettings.ChargeType.DIRECT,
    tax_mode=StripeSettings.TaxMode.STRIPE_TAX,
):
    config = StripeSettings.load()
    config.publishable_key = PUBLISHABLE_KEY
    config.secret_key = SECRET_KEY
    config.application_fee = application_fee
    config.charge_type = charge_type
    config.tax_mode = tax_mode
    config.allow_partial_refunds = allow_partial_refunds
    config.save()
    return config


def _peer_with_account(account_id):
    peer = make_peer()
    profile = peer.payment_profile
    profile.stripe_connect_account_id = AccountFactory(id=account_id)
    profile.save(update_fields=["stripe_connect_account_id", "updated_at"])
    return peer


def make_connected_peer(account_id=PEER_ACCOUNT_ID):
    return _peer_with_account(account_id)


def make_peer_with_account():
    return _peer_with_account(CONNECT_ACCOUNT_ID)


def make_peer_without_connected_account():
    peer = make_peer()
    profile = peer.payment_profile
    profile.stripe_connect_account_id = None
    profile.save(update_fields=["stripe_connect_account_id", "updated_at"])
    return peer


def make_booking(*, peer=None, total=BOOKING_TOTAL):
    peer = peer or make_connected_peer()
    booking = create_booking(
        meeting=create_meeting(peer=peer),
        seeker=UserFactory(),
        sessions=[{"requested_duration_minutes": SESSION_DURATION}],
    )
    booking.total_amount = total
    booking.save(update_fields=["total_amount", "updated_at"])
    return booking


def make_refund_meeting(*, refund_requires_approval, peer=None):
    return Meeting.objects.create(
        peer=peer or make_peer_with_account(),
        title="Test meeting",
        description="Test",
        meeting_type=MeetingType.ONE_ON_ONE,
        pricing_type=PricingType.FIXED,
        price=PAID_TOTAL,
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        refund_requires_approval=refund_requires_approval,
        currency="GBP",
        duration_minutes=30,
    )


def make_refund_request(*, refund_requires_approval, payment_intent_id="pi_test_123"):
    meeting = make_refund_meeting(refund_requires_approval=refund_requires_approval)
    request = MeetingRequest.objects.create(
        meeting=meeting,
        support_seeker=UserFactory(),
    )
    request.__dict__["status"] = MeetingRequestStatus.PAID
    request.stripe_payment_intent_id = payment_intent_id
    request.price_paid = PAID_TOTAL
    request.save()
    return request


class TestComputeTotal:
    def test_sums_session_prices(self):
        peer = make_connected_peer()
        meeting = create_meeting(peer=peer)
        tier = MeetingPriceTier.objects.create(
            meeting=meeting,
            duration_minutes=SESSION_DURATION,
        )
        MeetingPriceOption.objects.create(
            tier=tier,
            amount=TIER_PRICE,
            is_default=True,
        )
        booking = create_booking(
            meeting=meeting,
            seeker=UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        assert booking.compute_total() == TIER_PRICE


class TestCreateCheckoutSession:
    def test_missing_connect_account_raises(self):
        configure_stripe()
        booking = make_booking(peer=make_peer_without_connected_account())

        with pytest.raises(ValueError, match="no connected Stripe account"):
            booking.create_checkout_session(RequestFactory().get("/"))

    def test_ineligible_peer_raises(self):
        configure_stripe()
        meeting = create_meeting(peer=make_peer(is_approved=False))
        booking = Booking.objects.create(
            meeting=meeting,
            support_seeker=UserFactory(),
            total_amount=BOOKING_TOTAL,
            currency="GBP",
        )

        with pytest.raises(ValueError, match="not currently eligible"):
            booking.create_checkout_session(RequestFactory().get("/"))

    def test_not_ready_raises(self):
        booking = make_booking()

        with pytest.raises(ValueError, match="not configured"):
            booking.create_checkout_session(RequestFactory().get("/"))


class TestCreateRequestCheckoutSession:
    def test_missing_connect_account_raises(self):
        configure_stripe()
        meeting_request = MeetingRequest.objects.create(
            meeting=create_meeting(peer=make_peer_without_connected_account()),
            support_seeker=UserFactory(),
            status=MeetingRequestStatus.PENDING_PAYMENT,
        )

        with pytest.raises(ValueError, match="no connected Stripe account"):
            meeting_request.create_checkout_session(RequestFactory().get("/"))


class TestRefundFlow:
    def test_immediate_refund_issues_connected_account_refund(self):
        configure_stripe()
        request = make_refund_request(refund_requires_approval=False)
        with (
            patch(
                "neuromancers_network.meetings.models.refund.stripe.Refund.create",
            ) as create_refund,
            patch(
                "neuromancers_network.meetings.models.refund.StripeRefund.sync_from_stripe_data",
            ),
        ):
            create_refund.return_value = type("Refund", (), {"id": "re_123"})()
            refund_request = request.request_refund("Not happy")

        refund_request.refresh_from_db()
        assert refund_request.status == RefundStatus.REFUNDED
        assert refund_request.stripe_refund_id == "re_123"

    def test_approval_required_refund_stays_pending_until_peer_approval(self):
        configure_stripe()
        request = make_refund_request(refund_requires_approval=True)
        with (
            patch(
                "neuromancers_network.meetings.models.refund.stripe.Refund.create",
            ) as create_refund,
            patch(
                "neuromancers_network.meetings.models.refund.StripeRefund.sync_from_stripe_data",
            ),
        ):
            create_refund.return_value = type("Refund", (), {"id": "re_456"})()
            refund_request = request.request_refund("Need a refund")

        refund_request.refresh_from_db()
        assert refund_request.status == RefundStatus.PENDING
        assert refund_request.stripe_refund_id == ""

    def test_partial_refund_requires_toggle(self):
        configure_stripe()
        request = make_refund_request(refund_requires_approval=False)

        with pytest.raises(ValueError, match="Partial refunds are not enabled"):
            request.request_refund("Partial", amount="5.00")

    def test_partial_refund_sends_amount(self):
        configure_stripe(allow_partial_refunds=True)
        request = make_refund_request(refund_requires_approval=False)

        with (
            patch(
                "neuromancers_network.meetings.models.refund.stripe.Refund.create",
            ) as create_refund,
            patch(
                "neuromancers_network.meetings.models.refund.StripeRefund.sync_from_stripe_data",
            ),
        ):
            create_refund.return_value = type("Refund", (), {"id": "re_partial"})()
            request.request_refund("Partial", amount="5.00")

        assert create_refund.call_args.kwargs["amount"] == EXPECTED_PARTIAL_REFUND_MINOR

    def test_refund_exceeding_paid_amount_raises(self):
        configure_stripe(allow_partial_refunds=True)
        request = make_refund_request(refund_requires_approval=False)

        with pytest.raises(ValueError, match="exceeds the amount paid"):
            request.request_refund("Too much", amount="15.00")


class TestPaymentHistory:
    def _request(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return request

    def test_sync_records_receipt_url(self):
        seeker = UserFactory()
        booking = create_booking(
            meeting=create_meeting(peer=make_peer()),
            seeker=seeker,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )
        meeting_request = booking.sessions.first()

        with patch(
            "neuromancers_network.payments.services.receipt_url_for",
            return_value="https://receipt.example/r1",
        ):
            meeting_request.sync_payment_from_checkout("cs_x", "pi_x", 1000)

        meeting_request.refresh_from_db()
        assert meeting_request.receipt_url == "https://receipt.example/r1"

    def test_lists_only_signed_in_members_payments(self):
        seeker = UserFactory()
        booking = create_booking(
            meeting=create_meeting(peer=make_peer()),
            seeker=seeker,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )
        create_booking(
            meeting=create_meeting(peer=make_peer()),
            seeker=UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        results = user_payment_history(self._request(seeker))

        assert [row.pk for row in results] == [booking.sessions.first().pk]


class TestConnectedWebhooks:
    def _event(self, event_type, object_data, *, account=None):
        return SimpleNamespace(
            type=event_type,
            data={"object": object_data},
            default_api_key="sk_test",
            djstripe_owner_account=account,
        )

    def test_checkout_marks_booking_paid(self):
        configure_stripe()
        booking = make_booking()
        booking.stripe_checkout_session_id = "cs_paid"
        booking.save(update_fields=["stripe_checkout_session_id"])
        event = self._event(
            "checkout.session.completed",
            {"id": "cs_paid", "payment_intent": None, "amount_total": 2000},
        )

        from neuromancers_network.meetings.signals import (  # noqa: PLC0415
            handle_checkout_session_completed,
        )

        with patch(
            "neuromancers_network.meetings.signals.StripeSession.sync_from_stripe_data",
        ):
            handle_checkout_session_completed(sender=None, event=event)

        booking.refresh_from_db()
        assert booking.status == BookingStatus.PAID
