from decimal import Decimal

import pytest

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def make_meeting(*, approval_policy):
    return Meeting.objects.create(
        peer=UserFactory(),
        title="Test meeting",
        description="Test",
        meeting_type=MeetingType.ONE_ON_ONE,
        pricing_type=PricingType.FIXED,
        price=10,
        approval_policy=approval_policy,
        currency="GBP",
        scheduled_at=None,
        duration_minutes=30,
    )


def make_request(*, approval_policy):
    meeting = make_meeting(approval_policy=approval_policy)
    seeker = UserFactory()
    request = MeetingRequest(meeting=meeting, support_seeker=seeker)
    request.start()
    return request


class TestCheckoutSync:
    def test_sync_payment_updates_payment_fields(self):
        request = make_request(approval_policy=ApprovalPolicy.PAY_AFTER_JOIN)
        request.sync_payment_from_checkout("cs_test_1", "pi_test_1", 1000)
        request = MeetingRequest.objects.get(pk=request.pk)
        assert request.stripe_checkout_session_id == "cs_test_1"
        assert request.stripe_payment_intent_id == "pi_test_1"
        assert request.price_paid == Decimal("10")
        assert request.status == MeetingRequestStatus.PAID

    def test_sync_payment_is_idempotent(self):
        request = make_request(approval_policy=ApprovalPolicy.PAY_BEFORE_JOIN)
        request.sync_payment_from_checkout("cs_test_2", "pi_test_2", 1000)
        request.sync_payment_from_checkout("cs_test_2", "pi_test_2", 1000)
        request = MeetingRequest.objects.get(pk=request.pk)
        assert request.status == MeetingRequestStatus.PAID
