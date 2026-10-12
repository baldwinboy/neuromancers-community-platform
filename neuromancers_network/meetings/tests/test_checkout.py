from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import MeetingPriceOption
from neuromancers_network.meetings.models import MeetingPriceTier
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import AccountFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PUBLISHABLE_KEY = "pk_test_123"
SECRET_KEY = "sk_test_123"  # noqa: S105
PEER_ACCOUNT_ID = "acct_peer"
BOOKING_TOTAL = Decimal("20.00")
APPLICATION_FEE_PERCENT = 10
EXPECTED_APPLICATION_FEE_MINOR = 200
SESSION_DURATION = 30
TIER_PRICE = Decimal("15.00")
APPLICATION_FEE_AMOUNT = 250


def configure_stripe(
    *,
    application_fee=APPLICATION_FEE_PERCENT,
    charge_type=StripeSettings.ChargeType.DIRECT,
    tax_mode=StripeSettings.TaxMode.STRIPE_TAX,
):
    config = StripeSettings.load()
    config.publishable_key = PUBLISHABLE_KEY
    config.secret_key = SECRET_KEY
    config.application_fee = application_fee
    config.charge_type = charge_type
    config.tax_mode = tax_mode
    config.save()
    return config


def make_connected_peer():
    peer = make_peer()
    profile = peer.payment_profile
    profile.stripe_connect_account_id = AccountFactory(id=PEER_ACCOUNT_ID)
    profile.save(update_fields=["stripe_connect_account_id", "updated_at"])
    return peer


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
        assert (
            kwargs["payment_intent_data"]["application_fee_amount"]
            == APPLICATION_FEE_AMOUNT
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
