"""Recurring group-meeting generation."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.models import RecurrenceFrequency
from neuromancers_network.meetings.models import RecurrenceRule
from neuromancers_network.meetings.tasks import generate_recurring_group_meetings
from neuromancers_network.peers.tests.factories import make_peer

pytestmark = pytest.mark.django_db

TWO_OCCURRENCES = 2


def make_rule(**overrides):
    defaults = {
        "frequency": RecurrenceFrequency.WEEKLY,
        "interval": 1,
    }
    defaults.update(overrides)
    return RecurrenceRule.objects.create(**defaults)


def make_group_meeting(
    peer,
    rule,
    *,
    scheduled_at=None,
    status=MeetingStatus.PUBLISHED,
):
    meeting = Meeting(
        peer=peer,
        title="Group session",
        description="Test",
        meeting_type=MeetingType.GROUP,
        pricing_type=PricingType.FIXED,
        price=Decimal("10.00"),
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        currency="GBP",
        status=status,
        scheduled_at=scheduled_at or timezone.now() - timedelta(days=1),
        duration_minutes=60,
        max_participants=10,
        recurrence_rule=rule,
    )
    meeting.save(validate=False)
    return meeting


class TestGenerateRecurringGroupMeetings:
    def test_generates_next_publishable_occurrence(self):
        peer = make_peer()
        rule = make_rule()
        make_group_meeting(peer, rule)

        generate_recurring_group_meetings()

        occurrences = Meeting.objects.filter(recurrence_rule=rule).order_by(
            "scheduled_at",
        )
        assert occurrences.count() == TWO_OCCURRENCES
        latest = occurrences.last()
        assert latest.scheduled_at > timezone.now()
        assert latest.title == "Group session"
        assert latest.status == MeetingStatus.PUBLISHED

    def test_is_idempotent(self):
        peer = make_peer()
        rule = make_rule()
        make_group_meeting(peer, rule)

        generate_recurring_group_meetings()
        generate_recurring_group_meetings()

        assert Meeting.objects.filter(recurrence_rule=rule).count() == TWO_OCCURRENCES

    def test_ignores_draft_series(self):
        peer = make_peer()
        rule = make_rule()
        make_group_meeting(peer, rule, status=MeetingStatus.DRAFT)

        generate_recurring_group_meetings()

        assert Meeting.objects.filter(recurrence_rule=rule).count() == 1

    def test_respects_max_occurrences(self):
        peer = make_peer()
        rule = make_rule(max_occurrences=1)
        make_group_meeting(peer, rule)

        generate_recurring_group_meetings()

        assert Meeting.objects.filter(recurrence_rule=rule).count() == 1

    def test_respects_end_date(self):
        peer = make_peer()
        rule = make_rule(end_date=(timezone.now() + timedelta(days=1)).date())
        make_group_meeting(peer, rule)

        generate_recurring_group_meetings()

        assert Meeting.objects.filter(recurrence_rule=rule).count() == 1
