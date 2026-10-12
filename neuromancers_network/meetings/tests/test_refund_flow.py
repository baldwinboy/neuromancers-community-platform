from decimal import Decimal
from unittest.mock import patch

import pytest

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.models import RefundStatus
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import AccountFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

CONNECT_ACCOUNT_ID = "acct_refund"
SECRET_KEY = "sk_test_123"  # noqa: S105
PAID_TOTAL = Decimal("10.00")
AMOUNT = 500


def configure_stripe(
    *,
    allow_partial_refunds=False,
    charge_type=StripeSettings.ChargeType.DIRECT,
):
    config = StripeSettings.load()
    config.secret_key = SECRET_KEY
    config.charge_type = charge_type
    config.allow_partial_refunds = allow_partial_refunds
    config.save()
    return config


def make_peer_with_account():
    peer = make_peer()
    profile = peer.payment_profile
    profile.stripe_connect_account_id = AccountFactory(id=CONNECT_ACCOUNT_ID)
    profile.save(update_fields=["stripe_connect_account_id", "updated_at"])
    return peer


def make_meeting(*, refund_requires_approval, peer=None):
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


def make_request(*, refund_requires_approval, payment_intent_id="pi_test_123"):
    meeting = make_meeting(refund_requires_approval=refund_requires_approval)
    request = MeetingRequest.objects.create(
        meeting=meeting,
        support_seeker=UserFactory(),
    )
    request.__dict__["status"] = MeetingRequestStatus.PAID
    request.stripe_payment_intent_id = payment_intent_id
    request.price_paid = PAID_TOTAL
    request.save()
    return request


class TestRefundFlow:
    def test_immediate_refund_issues_connected_account_refund(self):
        configure_stripe()
        request = make_request(refund_requires_approval=False)
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
        request = make_request(refund_requires_approval=False)
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
        request = make_request(refund_requires_approval=True)
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
        request = make_request(refund_requires_approval=False)

        with pytest.raises(ValueError, match="Partial refunds are not enabled"):
            request.request_refund("Partial", amount="5.00")

    def test_partial_refund_sends_amount(self):
        configure_stripe(allow_partial_refunds=True)
        request = make_request(refund_requires_approval=False)

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

        assert create_refund.call_args.kwargs["amount"] == AMOUNT

    def test_refund_exceeding_paid_amount_raises(self):
        configure_stripe(allow_partial_refunds=True)
        request = make_request(refund_requires_approval=False)

        with pytest.raises(ValueError, match="exceeds the amount paid"):
            request.request_refund("Too much", amount="15.00")
