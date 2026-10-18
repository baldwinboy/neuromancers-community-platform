"""Calendar event materialisation from sessions and meetings."""

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
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.models import CalendarEvent
from neuromancers_network.peers.models.choices import CalendarEventKind
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

DURATION = 30


def make_request(
    meeting,
    *,
    status=MeetingRequestStatus.APPROVED,
    start=None,
):
    request = MeetingRequest(
        meeting=meeting,
        support_seeker=UserFactory(),
        status=status,
        requested_start_time=start or timezone.now() + timedelta(days=1),
        requested_duration_minutes=DURATION,
    )
    request.save(validate=False)
    return request


def make_group(status):
    meeting = Meeting(
        peer=make_peer(),
        title="Group session",
        description="Test",
        meeting_type=MeetingType.GROUP,
        pricing_type=PricingType.FIXED,
        price=Decimal("10.00"),
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        currency="GBP",
        scheduled_at=timezone.now() + timedelta(days=1),
        duration_minutes=60,
        max_participants=5,
        status=status,
    )
    meeting.save(validate=False)
    return meeting


class TestRequestEvents:
    def test_active_request_materialises_event(self):
        meeting = create_meeting(peer=make_peer())
        request = make_request(meeting)

        event = CalendarEvent.objects.get(source_type="request", source_id=request.pk)
        assert event.kind == CalendarEventKind.ONE_TO_ONE
        assert event.owner == meeting.peer

    def test_unapproved_request_has_no_event(self):
        meeting = create_meeting(peer=make_peer())
        request = make_request(meeting, status=MeetingRequestStatus.PENDING_APPROVAL)

        assert not CalendarEvent.objects.filter(
            source_type="request",
            source_id=request.pk,
        ).exists()

    def test_cancelled_request_removes_event(self):
        meeting = create_meeting(peer=make_peer())
        request = make_request(meeting)
        assert CalendarEvent.objects.filter(
            source_type="request",
            source_id=request.pk,
        ).exists()

        request.status = MeetingRequestStatus.CANCELLED
        request.save(validate=False)

        assert not CalendarEvent.objects.filter(
            source_type="request",
            source_id=request.pk,
        ).exists()


class TestMeetingEvents:
    def test_draft_has_no_event(self):
        meeting = make_group(MeetingStatus.DRAFT)

        assert not CalendarEvent.objects.filter(
            source_type="meeting",
            source_id=meeting.pk,
        ).exists()

    def test_published_materialises_public_event(self):
        meeting = make_group(MeetingStatus.PUBLISHED)

        event = CalendarEvent.objects.get(source_type="meeting", source_id=meeting.pk)
        assert event.kind == CalendarEventKind.GROUP
        assert event.is_public_detail is True

    def test_archived_removes_event(self):
        meeting = make_group(MeetingStatus.PUBLISHED)
        assert CalendarEvent.objects.filter(
            source_type="meeting",
            source_id=meeting.pk,
        ).exists()

        meeting.status = MeetingStatus.ARCHIVED
        meeting.save(validate=False)

        assert not CalendarEvent.objects.filter(
            source_type="meeting",
            source_id=meeting.pk,
        ).exists()
