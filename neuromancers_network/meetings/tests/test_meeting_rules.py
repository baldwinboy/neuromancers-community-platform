from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestMeetingRules:
    def test_group_meeting_must_start_at_least_30_minutes_in_future(self):
        meeting = Meeting(
            peer=UserFactory(),
            title="Group",
            description="Test",
            meeting_type=MeetingType.GROUP,
            pricing_type=PricingType.FIXED,
            price=10,
            approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
            currency="GBP",
            scheduled_at=timezone.now() + timedelta(minutes=20),
            duration_minutes=30,
        )

        with pytest.raises(ValidationError):
            meeting.full_clean()
