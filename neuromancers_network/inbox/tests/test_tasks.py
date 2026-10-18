"""Scheduled time-based notification tasks."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.inbox.tasks import emit_payment_reminders
from neuromancers_network.inbox.tasks import emit_session_reminders
from neuromancers_network.inbox.tasks import emit_upcoming_meetings
from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

SESSION_START_OFFSET_HOURS = 2
STALE_PAYMENT_HOURS = 48


def make_group_meeting(*, scheduled_at):
    meeting = Meeting(
        peer=make_peer(),
        title="Group session",
        description="Test",
        meeting_type=MeetingType.GROUP,
        pricing_type=PricingType.FIXED,
        price=Decimal("10.00"),
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        currency="GBP",
        scheduled_at=scheduled_at,
        duration_minutes=60,
        max_participants=5,
        status=MeetingStatus.PUBLISHED,
    )
    meeting.save(validate=False)
    return meeting


def make_group_request(
    meeting,
    *,
    seeker=None,
    status=MeetingRequestStatus.PAID,
):
    request = MeetingRequest(
        meeting=meeting,
        support_seeker=seeker or UserFactory(),
        status=status,
    )
    request.save(validate=False)
    return request


class TestSessionReminders:
    def test_emits_day_reminder_for_group_session(self):
        meeting = make_group_meeting(
            scheduled_at=timezone.now() + timedelta(hours=SESSION_START_OFFSET_HOURS),
        )
        request = make_group_request(meeting)

        emit_session_reminders()

        assert NotificationEventLog.objects.filter(
            event_type="session_reminder_1d",
            event_ref=f"meetingrequest.{request.pk}.reminder_1d",
        ).exists()

    def test_skips_inactive_sessions(self):
        meeting = make_group_meeting(
            scheduled_at=timezone.now() + timedelta(hours=SESSION_START_OFFSET_HOURS),
        )
        make_group_request(meeting, status=MeetingRequestStatus.CANCELLED)

        emit_session_reminders()

        assert not NotificationEventLog.objects.filter(
            event_type__startswith="session_reminder",
        ).exists()


class TestUpcomingMeetings:
    def test_includes_group_booking_seekers(self):
        meeting = make_group_meeting(
            scheduled_at=timezone.now() + timedelta(hours=SESSION_START_OFFSET_HOURS),
        )
        seeker = UserFactory()
        create_booking(meeting=meeting, seeker=seeker, sessions=[])

        emit_upcoming_meetings()

        log = NotificationEventLog.objects.get(
            event_type="meeting_upcoming",
            event_ref=f"meeting.{meeting.pk}.upcoming",
        )
        assert seeker.pk in log.payload["recipient_user_ids"]


class TestPaymentReminders:
    def test_emits_once_and_dedupes(self):
        meeting = create_meeting(peer=make_peer())
        request = MeetingRequest(
            meeting=meeting,
            support_seeker=UserFactory(),
            status=MeetingRequestStatus.PENDING_PAYMENT,
        )
        request.save(validate=False)
        MeetingRequest.objects.filter(pk=request.pk).update(
            created_at=timezone.now() - timedelta(hours=STALE_PAYMENT_HOURS),
        )

        emit_payment_reminders()
        emit_payment_reminders()

        assert (
            NotificationEventLog.objects.filter(
                event_type="payment_reminder_due",
                event_ref=f"meetingrequest.{request.pk}.payment_reminder",
            ).count()
            == 1
        )
