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
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def make_meeting(*, refund_requires_approval):
    return Meeting.objects.create(
        peer=UserFactory(),
        title="Test meeting",
        description="Test",
        meeting_type=MeetingType.ONE_ON_ONE,
        pricing_type=PricingType.FIXED,
        price=10,
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        refund_requires_approval=refund_requires_approval,
        currency="GBP",
        duration_minutes=30,
    )


def make_request(*, refund_requires_approval, payment_intent_id="pi_test_123"):
    meeting = make_meeting(refund_requires_approval=refund_requires_approval)
    seeker = UserFactory()
    StripeSettings.objects.create(secret_key="sk_test_123")  # noqa: S106
    request = MeetingRequest.objects.create(meeting=meeting, support_seeker=seeker)
    request.__dict__["status"] = MeetingRequestStatus.PAID
    request.stripe_payment_intent_id = payment_intent_id
    request.save()
    return request


class TestRefundFlow:
    def test_immediate_refund_requests_issue_stripe_refund(self):
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

    def test_approval_required_refund_stays_pending_until_peer_approval(self):
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
