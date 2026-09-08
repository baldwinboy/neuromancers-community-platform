from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.models import RecurrenceFrequency
from neuromancers_network.meetings.models import RecurrenceRule
from neuromancers_network.meetings.tasks import generate_recurring_group_meetings
from neuromancers_network.meetings.tasks import populate_pending_group_meeting_links
from neuromancers_network.meetings.tasks import populate_pending_meeting_links
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def make_group_meeting(*, scheduled_at, meeting_link=""):
    meeting = Meeting(
        peer=UserFactory(),
        title="Group",
        description="Test",
        meeting_type=MeetingType.GROUP,
        pricing_type=PricingType.FIXED,
        price=10,
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        currency="GBP",
        scheduled_at=scheduled_at,
        duration_minutes=30,
        meeting_link=meeting_link,
    )
    meeting.save(validate=False)
    return meeting


class TestMeetingTasks:
    def test_group_fallback_populates_missing_link_within_ten_minutes(self):
        make_group_meeting(scheduled_at=timezone.now() + timedelta(minutes=9))
        with patch(
            "neuromancers_network.meetings.models.meeting.Meeting.populate_meeting_link",
        ) as populate_link:
            populate_pending_group_meeting_links()
        populate_link.assert_called_once()

    def test_group_fallback_skips_outside_window(self):
        make_group_meeting(scheduled_at=timezone.now() + timedelta(minutes=20))
        with patch(
            "neuromancers_network.meetings.models.meeting.Meeting.populate_meeting_link",
        ) as populate_link:
            populate_pending_group_meeting_links()
        populate_link.assert_not_called()

    def test_recurring_group_meeting_generation_still_populates_link(self):
        expected_count = 2
        rule = RecurrenceRule.objects.create(frequency=RecurrenceFrequency.DAILY)
        meeting = make_group_meeting(scheduled_at=timezone.now() - timedelta(minutes=5))
        meeting.recurrence_rule = rule
        meeting.save(validate=False)

        with patch(
            "neuromancers_network.meetings.models.meeting.Meeting.populate_meeting_link",
        ) as populate_link:
            generate_recurring_group_meetings()

        assert Meeting.objects.filter(recurrence_rule=rule).count() == expected_count
        assert populate_link.call_count == 1

    def test_one_on_one_task_unchanged(self):
        populate_pending_meeting_links()
