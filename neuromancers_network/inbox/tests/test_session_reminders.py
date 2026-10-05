from datetime import timedelta

import pytest
from django.utils import timezone

from neuromancers_network.inbox.models.event_log import NotificationEventLog
from neuromancers_network.inbox.tasks import emit_session_reminders
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.users.tests.factories import UserFactory

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
