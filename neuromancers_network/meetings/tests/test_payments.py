from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.meetings.actions import bookings_checkout_many
from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingPriceOption
from neuromancers_network.meetings.models import MeetingPriceTier
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.models import RefundStatus
from neuromancers_network.meetings.models.booking import (
    create_checkout_session_for_bookings,
)
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
EXPECTED_APPLICATION_FEE_MINOR = 200
SESSION_DURATION = 30
LONGER_SESSION_DURATION = 60
TIER_PRICE = Decimal("15.00")
PAID_TOTAL = Decimal("10.00")
EXPECTED_REQUEST_FEE_MINOR = 250
EXPECTED_PARTIAL_REFUND_MINOR = 500
EXPECTED_LINE_ITEM_COUNT = 2
EXPECTED_PEER_SESSION_COUNT = 2
HTTP_REDIRECT = 302


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


def start_booking_checkout(booking, request):
    with (
        patch(
            "neuromancers_network.meetings.models.booking.stripe.checkout."
            "Session.create",
        ) as create_session,
        patch(
            "neuromancers_network.meetings.models.booking."
            "StripeSession.sync_from_stripe_data",
        ),
    ):
        create_session.return_value = type(
            "Session",
            (),
            {"id": "cs_1", "url": "https://checkout.example"},
        )()
        url = booking.create_checkout_session(request)
    return url, create_session.call_args.kwargs


def start_request_checkout(meeting_request, request):
    with (
        patch(
            "neuromancers_network.meetings.models.request.stripe.checkout."
            "Session.create",
        ) as create_session,
        patch(
            "neuromancers_network.meetings.models.request."
            "StripeSession.sync_from_stripe_data",
        ),
    ):
        create_session.return_value = type(
            "Session",
            (),
            {"id": "cs_2", "url": "https://checkout.example/request"},
        )()
        url = meeting_request.create_checkout_session(request)
    return url, create_session.call_args.kwargs


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
    def test_direct_charge_and_fee(self):
        configure_stripe()
        booking = make_booking()

        url, kwargs = start_booking_checkout(booking, RequestFactory().get("/"))

        assert url == "https://checkout.example"
        assert kwargs["stripe_account"] == PEER_ACCOUNT_ID
        assert kwargs["automatic_tax"] == {"enabled": True}
        payment_intent_data = kwargs["payment_intent_data"]
        assert "transfer_data" not in payment_intent_data
        assert (
            payment_intent_data["application_fee_amount"]
            == EXPECTED_APPLICATION_FEE_MINOR
        )
        line_item = kwargs["line_items"][0]
        assert line_item["price_data"]["currency"] == "gbp"
        assert line_item["price_data"]["unit_amount"] == int(BOOKING_TOTAL * 100)

    def test_destination_charge_and_fee(self):
        configure_stripe(charge_type=StripeSettings.ChargeType.DESTINATION)
        booking = make_booking()

        _url, kwargs = start_booking_checkout(booking, RequestFactory().get("/"))

        assert "stripe_account" not in kwargs
        payment_intent_data = kwargs["payment_intent_data"]
        assert payment_intent_data["transfer_data"]["destination"] == PEER_ACCOUNT_ID
        assert (
            payment_intent_data["application_fee_amount"]
            == EXPECTED_APPLICATION_FEE_MINOR
        )

    def test_tax_disabled_when_off(self):
        configure_stripe(tax_mode=StripeSettings.TaxMode.OFF)
        booking = make_booking()

        _url, kwargs = start_booking_checkout(booking, RequestFactory().get("/"))

        assert "automatic_tax" not in kwargs

    def test_separate_charge_has_no_fee(self):
        configure_stripe(charge_type=StripeSettings.ChargeType.SEPARATE)
        booking = make_booking()

        _url, kwargs = start_booking_checkout(booking, RequestFactory().get("/"))

        assert "stripe_account" not in kwargs
        assert "payment_intent_data" not in kwargs

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
    def test_direct_charge_and_tier_price(self):
        configure_stripe()
        peer = make_connected_peer()
        meeting = create_meeting(peer=peer)
        meeting_request = MeetingRequest.objects.create(
            meeting=meeting,
            support_seeker=UserFactory(),
            status=MeetingRequestStatus.PENDING_PAYMENT,
            requested_duration_minutes=SESSION_DURATION,
        )

        url, kwargs = start_request_checkout(
            meeting_request,
            RequestFactory().get("/"),
        )

        assert url == "https://checkout.example/request"
        assert kwargs["stripe_account"] == PEER_ACCOUNT_ID
        assert kwargs["metadata"] == {"meeting_request_id": str(meeting_request.pk)}
        assert kwargs["payment_intent_data"]["application_fee_amount"] == (
            EXPECTED_REQUEST_FEE_MINOR
        )

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
        kwargs = create_refund.call_args.kwargs
        assert kwargs["payment_intent"] == "pi_test_123"
        assert kwargs["stripe_account"] == CONNECT_ACCOUNT_ID
        assert kwargs["refund_application_fee"] is True
        assert "amount" not in kwargs

    def test_destination_refund_reverses_transfer(self):
        configure_stripe(charge_type=StripeSettings.ChargeType.DESTINATION)
        request = make_refund_request(refund_requires_approval=False)
        with (
            patch(
                "neuromancers_network.meetings.models.refund.stripe.Refund.create",
            ) as create_refund,
            patch(
                "neuromancers_network.meetings.models.refund.StripeRefund.sync_from_stripe_data",
            ),
        ):
            create_refund.return_value = type("Refund", (), {"id": "re_dest"})()
            request.request_refund("Not happy")

        kwargs = create_refund.call_args.kwargs
        assert kwargs["reverse_transfer"] is True
        assert kwargs["refund_application_fee"] is True
        assert "stripe_account" not in kwargs

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


class TestCartCheckout:
    def test_groups_multiple_bookings_per_peer_into_one_session(self):
        configure_stripe()
        meeting = create_meeting(peer=make_connected_peer())
        seeker = UserFactory()
        first = create_booking(
            meeting=meeting,
            seeker=seeker,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )
        second = create_booking(
            meeting=meeting,
            seeker=seeker,
            sessions=[{"requested_duration_minutes": LONGER_SESSION_DURATION}],
        )

        with (
            patch(
                "neuromancers_network.meetings.models.booking.stripe.checkout."
                "Session.create",
            ) as create_session,
            patch(
                "neuromancers_network.meetings.models.booking."
                "StripeSession.sync_from_stripe_data",
            ),
        ):
            create_session.return_value = type(
                "Session",
                (),
                {"id": "cs_cart", "url": "https://cart.example"},
            )()
            url = create_checkout_session_for_bookings(
                [first, second],
                RequestFactory().get("/"),
            )

        assert url == "https://cart.example"
        assert create_session.call_count == 1
        assert (
            len(create_session.call_args.kwargs["line_items"])
            == EXPECTED_LINE_ITEM_COUNT
        )

    def test_one_session_per_peer(self):
        configure_stripe()
        seeker = UserFactory()
        first = create_booking(
            meeting=create_meeting(peer=make_connected_peer("acct_p1")),
            seeker=seeker,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )
        second = create_booking(
            meeting=create_meeting(peer=make_connected_peer("acct_p2")),
            seeker=seeker,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        with (
            patch(
                "neuromancers_network.meetings.models.booking.stripe.checkout."
                "Session.create",
            ) as create_session,
            patch(
                "neuromancers_network.meetings.models.booking."
                "StripeSession.sync_from_stripe_data",
            ),
        ):
            create_session.return_value = type(
                "Session",
                (),
                {"id": "cs", "url": "https://cart.example"},
            )()
            create_checkout_session_for_bookings(
                [first, second],
                RequestFactory().get("/"),
            )

        assert create_session.call_count == EXPECTED_PEER_SESSION_COUNT

    def test_action_redirects_to_first_session(self):
        configure_stripe()
        booking = make_booking()
        request = RequestFactory().post("/", {})
        request.user = booking.support_seeker

        with (
            patch(
                "neuromancers_network.meetings.models.booking.stripe.checkout."
                "Session.create",
            ) as create_session,
            patch(
                "neuromancers_network.meetings.models.booking."
                "StripeSession.sync_from_stripe_data",
            ),
        ):
            create_session.return_value = type(
                "Session",
                (),
                {"id": "cs_many", "url": "https://cart.example"},
            )()
            response = bookings_checkout_many(
                request,
                {"bookings": [booking.pk]},
            )

        assert response.status_code == HTTP_REDIRECT
        assert response.url == "https://cart.example"
