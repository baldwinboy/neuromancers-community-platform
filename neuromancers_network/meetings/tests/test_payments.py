from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import RequestFactory
from django.utils import timezone

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

    def test_refund_exceeding_paid_amount_raises(self):
        configure_stripe(allow_partial_refunds=True)
        request = make_refund_request(refund_requires_approval=False)

        with pytest.raises(ValueError, match="exceeds the amount paid"):
            request.request_refund("Too much", amount="15.00")

    def test_partial_refund_without_recorded_payment_raises(self):
        configure_stripe(allow_partial_refunds=True)
        request = make_refund_request(refund_requires_approval=False)
        request.price_paid = None
        request.save(update_fields=["price_paid", "updated_at"])

        with pytest.raises(ValueError, match="no recorded payment"):
            request.request_refund("Partial", amount="5.00")

    def test_rejected_refund_can_be_raised_again(self):
        configure_stripe()
        request = make_refund_request(refund_requires_approval=True)
        refund_request = request.request_refund("First attempt")
        refund_request.reject()
        refund_request.save()

        raised_again = request.request_refund("Second attempt")

        assert raised_again.status == RefundStatus.PENDING
        assert raised_again.reason == "Second attempt"


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


class TestPerItemStripeAmounts:
    def _event(self, object_data, *, account=None):
        return SimpleNamespace(
            type="checkout.session.completed",
            data={"object": object_data},
            default_api_key="sk_test",
            djstripe_owner_account=account,
        )

    def _line_items(self, *amounts):
        return SimpleNamespace(
            data=[
                SimpleNamespace(id=f"li_{index}", amount_total=amount)
                for index, amount in enumerate(amounts)
            ],
            has_more=False,
        )

    def _session_kwargs(self, bookings, request=None):
        from neuromancers_network.meetings.models.booking import _peer_session_kwargs  # noqa: PLC0415

        return _peer_session_kwargs(
            bookings,
            request or RequestFactory().get("/"),
            StripeSettings.load(),
            None,
        )

    def _dispatch(self, event, line_items):
        from neuromancers_network.meetings.signals import (  # noqa: PLC0415
            handle_checkout_session_completed,
        )

        with (
            patch(
                "neuromancers_network.meetings.signals."
                "stripe.checkout.Session.list_line_items",
                return_value=line_items,
            ),
            patch(
                "neuromancers_network.meetings.signals.stripe.PaymentIntent.retrieve",
                return_value={},
            ),
            patch("neuromancers_network.meetings.signals.sync_from_event"),
            patch(
                "neuromancers_network.payments.services.receipt_url_for",
                return_value="https://receipt.example/1",
            ),
        ):
            handle_checkout_session_completed(sender=None, event=event)

    def test_requests_get_their_own_stripe_amount(self):
        configure_stripe()
        peer = make_connected_peer()
        meeting = create_meeting(peer=peer)
        short = MeetingPriceTier.objects.create(
            meeting=meeting,
            duration_minutes=SESSION_DURATION,
        )
        MeetingPriceOption.objects.create(
            tier=short,
            amount=Decimal("10.00"),
            is_default=True,
        )
        long = MeetingPriceTier.objects.create(meeting=meeting, duration_minutes=60)
        MeetingPriceOption.objects.create(
            tier=long,
            amount=Decimal("25.00"),
            is_default=True,
        )
        start = timezone.now() + timedelta(days=2)
        booking = create_booking(
            meeting=meeting,
            seeker=UserFactory(),
            sessions=[
                {
                    "requested_start_time": start,
                    "requested_duration_minutes": SESSION_DURATION,
                },
                {
                    "requested_start_time": start + timedelta(hours=1),
                    "requested_duration_minutes": 60,
                },
            ],
        )
        requests = list(booking.sessions.order_by("pk"))
        session_kwargs = self._session_kwargs([booking])

        booking.stripe_checkout_session_id = "cs_per_item"
        booking.save(update_fields=["stripe_checkout_session_id"])
        event = self._event(
            {
                "id": "cs_per_item",
                "payment_intent": "pi_per_item",
                "amount_total": 3900,
                "metadata": session_kwargs["metadata"],
            },
        )
        self._dispatch(event, self._line_items(1100, 2800))

        for meeting_request, expected in zip(
            requests,
            (Decimal("11.00"), Decimal("28.00")),
            strict=True,
        ):
            meeting_request.refresh_from_db()
            assert meeting_request.status == MeetingRequestStatus.PAID
            assert meeting_request.price_paid == expected
            assert meeting_request.stripe_payment_intent_id == "pi_per_item"
            assert meeting_request.stripe_checkout_session_id == "cs_per_item"
        booking.refresh_from_db()
        assert booking.status == BookingStatus.PAID
        assert booking.total_amount == Decimal("39.00")

    def test_sessionless_booking_gets_its_own_stripe_amount(self):
        configure_stripe()
        booking = Booking.objects.create(
            meeting=create_meeting(peer=make_connected_peer()),
            support_seeker=UserFactory(),
            total_amount=Decimal("20.00"),
            currency="GBP",
        )
        session_kwargs = self._session_kwargs([booking])

        booking.stripe_checkout_session_id = "cs_booking"
        booking.save(update_fields=["stripe_checkout_session_id"])
        event = self._event(
            {
                "id": "cs_booking",
                "payment_intent": "pi_booking",
                "amount_total": 2100,
                "metadata": session_kwargs["metadata"],
            },
        )
        self._dispatch(event, self._line_items(2100))

        booking.refresh_from_db()
        assert booking.status == BookingStatus.PAID
        assert booking.total_amount == Decimal("21.00")

    def test_multiple_bookings_in_one_session(self):
        configure_stripe()
        peer = make_connected_peer()
        seeker = UserFactory()
        first = create_booking(
            meeting=create_meeting(peer=peer, title="First"),
            seeker=seeker,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )
        second = create_booking(
            meeting=create_meeting(peer=peer, title="Second"),
            seeker=seeker,
            sessions=[{"requested_duration_minutes": 60}],
        )
        first_request = first.sessions.get()
        second_request = second.sessions.get()
        session_kwargs = self._session_kwargs([first, second])

        first.stripe_checkout_session_id = "cs_multi"
        first.save(update_fields=["stripe_checkout_session_id"])
        second.stripe_checkout_session_id = "cs_multi"
        second.save(update_fields=["stripe_checkout_session_id"])
        event = self._event(
            {
                "id": "cs_multi",
                "payment_intent": "pi_multi",
                "amount_total": 3900,
                "metadata": session_kwargs["metadata"],
            },
        )
        self._dispatch(event, self._line_items(1100, 2800))

        first_request.refresh_from_db()
        second_request.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        assert first_request.price_paid == Decimal("11.00")
        assert second_request.price_paid == Decimal("28.00")
        assert first.total_amount == Decimal("11.00")
        assert second.total_amount == Decimal("28.00")

    def test_replayed_checkout_event_is_idempotent(self):
        configure_stripe()
        peer = make_connected_peer()
        booking = create_booking(
            meeting=create_meeting(peer=peer),
            seeker=UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )
        meeting_request = booking.sessions.get()
        session_kwargs = self._session_kwargs([booking])
        booking.stripe_checkout_session_id = "cs_replay"
        booking.save(update_fields=["stripe_checkout_session_id"])
        event = self._event(
            {
                "id": "cs_replay",
                "payment_intent": "pi_replay",
                "amount_total": 1100,
                "metadata": session_kwargs["metadata"],
            },
        )

        self._dispatch(event, self._line_items(1100))
        self._dispatch(event, self._line_items(1100))

        meeting_request.refresh_from_db()
        booking.refresh_from_db()
        assert meeting_request.status == MeetingRequestStatus.PAID
        assert meeting_request.price_paid == Decimal("11.00")
        assert booking.status == BookingStatus.PAID
        assert booking.total_amount == Decimal("11.00")


class TestMultiPeerCart:
    def _booking(self, peer, *, title="Meeting", seeker=None):
        return create_booking(
            meeting=create_meeting(peer=peer, title=title),
            seeker=seeker or UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

    def test_service_rejects_mixed_peers(self):
        from neuromancers_network.meetings.models.booking import (  # noqa: PLC0415
            create_checkout_session_for_bookings,
        )

        first = self._booking(make_connected_peer("acct_first"), title="First")
        second = self._booking(make_connected_peer("acct_second"), title="Second")

        with pytest.raises(ValueError, match="one care provider"):
            create_checkout_session_for_bookings(
                [first, second],
                RequestFactory().get("/"),
            )

    def test_action_shows_error_for_mixed_peers(self):
        from django.contrib.messages import get_messages  # noqa: PLC0415
        from django.contrib.messages.middleware import MessageMiddleware  # noqa: PLC0415
        from django.contrib.sessions.middleware import SessionMiddleware  # noqa: PLC0415

        from neuromancers_network.meetings.actions import bookings_checkout_many  # noqa: PLC0415

        seeker = UserFactory()
        first = self._booking(
            make_connected_peer("acct_first"),
            title="First",
            seeker=seeker,
        )
        second = self._booking(
            make_connected_peer("acct_second"),
            title="Second",
            seeker=seeker,
        )

        request = RequestFactory().post("/", {"bookings": [first.pk, second.pk]})
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        request.user = seeker
        response = bookings_checkout_many(request, request.POST)

        assert response.status_code == HTTPStatus.FOUND
        assert any(
            "one care provider" in str(message) for message in get_messages(request)
        )
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.stripe_checkout_session_id == ""
        assert second.stripe_checkout_session_id == ""

    def test_service_rejects_mixed_currency(self):
        from neuromancers_network.meetings.models.booking import (  # noqa: PLC0415
            create_checkout_session_for_bookings,
        )

        configure_stripe()
        peer = make_connected_peer()
        seeker = UserFactory()
        gbp_booking = self._booking(peer, title="GBP", seeker=seeker)
        usd_meeting = create_meeting(peer=peer, title="USD")
        usd_meeting.currency = "USD"
        usd_meeting.save(validate=False)
        usd_booking = create_booking(
            meeting=usd_meeting,
            seeker=seeker,
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        with pytest.raises(ValueError, match="one care provider and currency"):
            create_checkout_session_for_bookings(
                [gbp_booking, usd_booking],
                RequestFactory().get("/"),
            )

    def test_service_accepts_single_peer(self):
        from neuromancers_network.meetings.models.booking import (  # noqa: PLC0415
            create_checkout_session_for_bookings,
        )

        configure_stripe()
        peer = make_connected_peer()
        first = self._booking(peer, title="First")
        second = self._booking(peer, title="Second")

        with (
            patch(
                "neuromancers_network.meetings.models.booking."
                "stripe.checkout.Session.create",
                return_value=SimpleNamespace(id="cs_cart", url="https://checkout"),
            ),
            patch(
                "neuromancers_network.meetings.models.booking."
                "StripeSession.sync_from_stripe_data",
            ),
        ):
            url = create_checkout_session_for_bookings(
                [first, second],
                RequestFactory().get("/"),
            )

        assert url == "https://checkout"
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.stripe_checkout_session_id == "cs_cart"
        assert second.stripe_checkout_session_id == "cs_cart"


class TestPricing:
    def _duration_tier_meeting(self):
        meeting = create_meeting(peer=make_connected_peer())
        meeting.pricing_type = PricingType.DURATION_TIERS
        meeting.price = None
        meeting.save(validate=False)
        return meeting

    def test_duration_tier_without_tier_returns_none(self):
        meeting = self._duration_tier_meeting()

        assert meeting.price_for(SESSION_DURATION) is None

    def test_fixed_pricing_falls_back_to_meeting_price(self):
        meeting = create_meeting(peer=make_connected_peer())

        assert meeting.price_for(SESSION_DURATION) == Decimal("25.00")

    def test_compute_total_raises_without_tier_price(self):
        meeting = self._duration_tier_meeting()
        booking = create_booking(
            meeting=meeting,
            seeker=UserFactory(),
            sessions=[{"requested_duration_minutes": SESSION_DURATION}],
        )

        with pytest.raises(ValueError, match="no resolvable price"):
            booking.compute_total()

    def test_sessionless_booking_without_price_raises(self):
        meeting = self._duration_tier_meeting()
        booking = Booking.objects.create(
            meeting=meeting,
            support_seeker=UserFactory(),
        )

        with pytest.raises(ValueError, match="no amount to charge"):
            booking.compute_total()


class TestCurrencyCapture:
    def test_sync_persists_base_amount_and_rate(self):
        meeting = create_meeting(peer=make_peer())
        meeting.currency = "USD"
        meeting.save(validate=False)
        meeting_request = MeetingRequest.objects.create(
            meeting=meeting,
            support_seeker=UserFactory(),
            status=MeetingRequestStatus.PAID,
        )

        meeting_request.sync_payment_from_checkout(
            "cs_currency",
            "pi_currency",
            1000,
            currency_conversion={
                "currency": "GBP",
                "amount": 800,
                "source_currency": "USD",
                "target_currency": "GBP",
            },
        )

        meeting_request.refresh_from_db()
        assert meeting_request.price_paid == Decimal("10.00")
        assert meeting_request.price_paid_currency == "USD"
        assert meeting_request.price_paid_base == Decimal("8.00")
        assert meeting_request.price_paid_rate == Decimal("0.80000000")

    def test_same_currency_records_one_to_one(self):
        meeting = create_meeting(peer=make_peer())
        meeting_request = MeetingRequest.objects.create(
            meeting=meeting,
            support_seeker=UserFactory(),
            status=MeetingRequestStatus.PAID,
        )

        meeting_request.sync_payment_from_checkout("cs_gbp", "pi_gbp", 2500)

        meeting_request.refresh_from_db()
        assert meeting_request.price_paid_base == Decimal("25.00")
        assert meeting_request.price_paid_rate == Decimal("1")
