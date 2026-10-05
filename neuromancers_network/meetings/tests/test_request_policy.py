from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def make_meeting(*, approval_policy):
    return Meeting(
        peer=UserFactory(),
        title="Test meeting",
        description="Test",
        meeting_type=MeetingType.ONE_ON_ONE,
        pricing_type=PricingType.FIXED,
        approval_policy=approval_policy,
        currency="GBP",
        scheduled_at=timezone.now(),
        duration_minutes=30,
    )


def make_request(*, approval_policy):
    meeting = make_meeting(approval_policy=approval_policy)
    seeker = UserFactory()
    request = MeetingRequest(meeting=meeting, support_seeker=seeker)
    request.start()
    return request


class TestApprovalPolicy:
    def test_approval_required_starts_pending_approval(self):
        request = make_request(approval_policy=ApprovalPolicy.APPROVAL_REQUIRED)
        assert request.status == MeetingRequestStatus.PENDING_APPROVAL
        assert request.requires_approval is True
        assert request.requires_payment_before_join is False
        assert request.can_join is False
        assert request.can_pay is False

    def test_approval_required_then_paid_before_join(self):
        request = make_request(approval_policy=ApprovalPolicy.APPROVAL_REQUIRED)
        request.approve()
        assert request.status == MeetingRequestStatus.APPROVED
        assert request.can_join is True
        assert request.can_pay is True
        request.mark_paid()
        assert request.status == MeetingRequestStatus.PAID
        assert request.can_join is True

    def test_pay_before_join_starts_pending_payment(self):
        request = make_request(approval_policy=ApprovalPolicy.PAY_BEFORE_JOIN)
        assert request.status == MeetingRequestStatus.PENDING_PAYMENT
        assert request.requires_approval is False
        assert request.requires_payment_before_join is True
        assert request.can_join is False
        assert request.can_pay is True

    def test_pay_before_join_can_only_join_after_paid(self):
        request = make_request(approval_policy=ApprovalPolicy.PAY_BEFORE_JOIN)
        request.mark_paid()
        assert request.status == MeetingRequestStatus.PAID
        assert request.can_join is True

    def test_pay_after_join_starts_approved(self):
        request = make_request(approval_policy=ApprovalPolicy.PAY_AFTER_JOIN)
        assert request.status == MeetingRequestStatus.APPROVED
        assert request.requires_approval is False
        assert request.requires_payment_before_join is False
        assert request.allows_join_before_payment is True
        assert request.can_join is True
        assert request.can_pay is True

    def test_pay_after_join_can_pay_later(self):
        request = make_request(approval_policy=ApprovalPolicy.PAY_AFTER_JOIN)
        request.mark_paid()
        assert request.status == MeetingRequestStatus.PAID

    def test_one_on_one_request_must_start_at_least_10_minutes_after_meeting_creation(
        self,
    ):
        meeting = make_meeting(approval_policy=ApprovalPolicy.APPROVAL_REQUIRED)
        meeting.save()
        seeker = UserFactory()
        request = MeetingRequest(
            meeting=meeting,
            support_seeker=seeker,
            requested_start_time=meeting.created_at + timedelta(minutes=5),
        )

        with pytest.raises(ValidationError):
            request.full_clean()
