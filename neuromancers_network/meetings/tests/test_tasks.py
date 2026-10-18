"""Scheduled meeting tasks."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.tasks import mark_completed_sessions
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

DURATION = 30


def make_meeting(peer, *, meeting_type=MeetingType.ONE_ON_ONE, scheduled_at=None):
    meeting = Meeting(
        peer=peer,
        title="Scheduled session",
        description="Test",
        meeting_type=meeting_type,
        pricing_type=PricingType.FIXED,
        price=Decimal("10.00"),
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        currency="GBP",
        status=MeetingStatus.PUBLISHED,
        scheduled_at=scheduled_at,
        duration_minutes=DURATION,
        max_participants=5 if meeting_type == MeetingType.GROUP else None,
    )
    meeting.save(validate=False)
    return meeting


def make_request(
    meeting,
    *,
    status=MeetingRequestStatus.PAID,
    start=None,
    duration=None,
):
    request = MeetingRequest(
        meeting=meeting,
        support_seeker=UserFactory(),
        status=status,
        requested_start_time=start,
        requested_duration_minutes=duration,
    )
    request.save(validate=False)
    return request


class TestMarkCompletedSessions:
    def test_completes_111_session_after_end(self):
        meeting = make_meeting(make_peer())
        request = make_request(
            meeting,
            start=timezone.now() - timedelta(hours=2),
            duration=DURATION,
        )

        mark_completed_sessions()

        request.refresh_from_db()
        assert request.status == MeetingRequestStatus.COMPLETED

    def test_keeps_in_progress_session_paid(self):
        meeting = make_meeting(make_peer())
        request = make_request(
            meeting,
            start=timezone.now() - timedelta(minutes=10),
            duration=DURATION,
        )

        mark_completed_sessions()

        request.refresh_from_db()
        assert request.status == MeetingRequestStatus.PAID

    def test_completes_group_request_after_meeting_end(self):
        meeting = make_meeting(
            make_peer(),
            meeting_type=MeetingType.GROUP,
            scheduled_at=timezone.now() - timedelta(hours=2),
        )
        request = make_request(meeting)

        mark_completed_sessions()

        request.refresh_from_db()
        assert request.status == MeetingRequestStatus.COMPLETED

    def test_ignores_unpaid_requests(self):
        meeting = make_meeting(make_peer())
        request = make_request(
            meeting,
            status=MeetingRequestStatus.APPROVED,
            start=timezone.now() - timedelta(hours=2),
            duration=DURATION,
        )

        mark_completed_sessions()

        request.refresh_from_db()
        assert request.status == MeetingRequestStatus.APPROVED

    def test_ignores_request_without_schedule(self):
        meeting = make_meeting(make_peer())
        request = make_request(meeting)

        mark_completed_sessions()

        request.refresh_from_db()
        assert request.status == MeetingRequestStatus.PAID
