from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.meetings.models import MeetingPriceOption
from neuromancers_network.meetings.models import MeetingPriceTier
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.users.tests.factories import AccountFactory
from neuromancers_network.users.tests.factories import PaymentProfileFactory
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


def configure_stripe(*, application_fee=APPLICATION_FEE_PERCENT):
    config = StripeSettings.load()
    config.publishable_key = PUBLISHABLE_KEY
    config.secret_key = SECRET_KEY
    config.application_fee = application_fee
    config.save()
    return config


def make_connected_peer():
    peer = UserFactory()
    PaymentProfileFactory(
        user=peer,
        stripe_connect_account_id=AccountFactory(id=PEER_ACCOUNT_ID),
    )
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


class TestCreateCheckoutSession:
    def test_destination_charge_and_fee(self):
        configure_stripe()
        booking = make_booking()
        request = RequestFactory().get("/")

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

        assert url == "https://checkout.example"
        _, kwargs = create_session.call_args
        payment_intent_data = kwargs["payment_intent_data"]
        assert payment_intent_data["transfer_data"]["destination"] == PEER_ACCOUNT_ID
        assert (
            payment_intent_data["application_fee_amount"]
            == EXPECTED_APPLICATION_FEE_MINOR
        )
        line_item = kwargs["line_items"][0]
        assert line_item["price_data"]["currency"] == "gbp"
        assert line_item["price_data"]["unit_amount"] == int(BOOKING_TOTAL * 100)

    def test_missing_connect_account_raises(self):
        configure_stripe()
        peer = UserFactory()
        PaymentProfileFactory(user=peer, stripe_connect_account_id=None)
        booking = make_booking(peer=peer)

        with pytest.raises(ValueError, match="no connected Stripe account"):
            booking.create_checkout_session(RequestFactory().get("/"))

    def test_not_ready_raises(self):
        booking = make_booking()

        with pytest.raises(ValueError, match="not configured"):
            booking.create_checkout_session(RequestFactory().get("/"))
