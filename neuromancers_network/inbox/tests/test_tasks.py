from datetime import timedelta

import pytest
from django.utils import timezone

import neuromancers_network.inbox.tasks as tasks_module
from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.inbox.tasks import emit_payment_reminders
from neuromancers_network.inbox.tasks import emit_session_reminders
from neuromancers_network.inbox.tasks import emit_upcoming_meetings
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.users.tests.factories import UserFactory

from .factories import make_meeting
from .factories import make_request

pytestmark = pytest.mark.django_db

SESSION_DURATION = 30


def make_session(*, hours_ahead):
    request = MeetingRequest(
        meeting=create_meeting(peer=UserFactory()),
        support_seeker=UserFactory(),
        requested_start_time=timezone.now() + timedelta(hours=hours_ahead),
        requested_duration_minutes=SESSION_DURATION,
        status=MeetingRequestStatus.PAID,
    )
    request.save(validate=False)
    return request


def _make_stale_pending_request():
    meeting = make_meeting(UserFactory())
    request = make_request(meeting)
    request.__dict__["status"] = MeetingRequestStatus.PENDING_PAYMENT
    request.save()
    MeetingRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now() - timedelta(hours=2),
    )
    return request


class TestPaymentReminders:
    def test_emits_for_stale_pending_payment_request(self, monkeypatch):
        monkeypatch.setattr(tasks_module, "PAYMENT_REMINDER_AFTER_HOURS", 0)
        request = _make_stale_pending_request()

        emit_payment_reminders()

        ref = f"meetingrequest.{request.pk}.payment_reminder"
        assert NotificationEventLog.objects.filter(
            event_type="payment_reminder_due",
            event_ref=ref,
        ).exists()

    def test_is_idempotent(self, monkeypatch):
        monkeypatch.setattr(tasks_module, "PAYMENT_REMINDER_AFTER_HOURS", 0)
        _make_stale_pending_request()

        emit_payment_reminders()
        emit_payment_reminders()

        assert (
            NotificationEventLog.objects.filter(
                event_type="payment_reminder_due",
            ).count()
            == 1
        )


class TestUpcomingMeetings:
    def test_emits_for_published_group_meeting_in_window(self):
        peer = UserFactory()
        meeting = make_meeting(
            peer,
            meeting_type=MeetingType.GROUP,
        )
        make_request(meeting, UserFactory())

        emit_upcoming_meetings()

        ref = f"meeting.{meeting.pk}.upcoming"
        assert NotificationEventLog.objects.filter(
            event_type="meeting_upcoming",
            event_ref=ref,
        ).exists()

    def test_is_idempotent(self):
        peer = UserFactory()
        meeting = make_meeting(
            peer,
            meeting_type=MeetingType.GROUP,
        )
        make_request(meeting, UserFactory())

        emit_upcoming_meetings()
        emit_upcoming_meetings()

        assert (
            NotificationEventLog.objects.filter(
                event_type="meeting_upcoming",
            ).count()
            == 1
        )

    def test_skips_meetings_without_bookings(self):
        meeting = make_meeting(UserFactory(), meeting_type=MeetingType.GROUP)

        emit_upcoming_meetings()

        assert not NotificationEventLog.objects.filter(
            event_type="meeting_upcoming",
            event_ref=f"meeting.{meeting.pk}.upcoming",
        ).exists()


class TestSessionReminders:
    def test_day_ahead_reminder(self):
        session = make_session(hours_ahead=12)

        emit_session_reminders()

        assert NotificationEventLog.objects.filter(
            event_type="session_reminder_1d",
            event_ref=f"meetingrequest.{session.pk}.reminder_1d",
        ).exists()

    def test_hour_ahead_reminder(self):
        session = make_session(hours_ahead=0.5)

        emit_session_reminders()

        assert NotificationEventLog.objects.filter(
            event_type="session_reminder_1h",
            event_ref=f"meetingrequest.{session.pk}.reminder_1h",
        ).exists()

    def test_is_idempotent(self):
        session = make_session(hours_ahead=12)

        emit_session_reminders()
        emit_session_reminders()

        assert (
            NotificationEventLog.objects.filter(
                event_ref=f"meetingrequest.{session.pk}.reminder_1d",
            ).count()
            == 1
        )
