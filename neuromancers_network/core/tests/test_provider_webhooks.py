from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from django.urls import reverse
from django.utils import timezone

from neuromancers_network.analytics.metrics import PERIOD_ALL_TIME
from neuromancers_network.analytics.metrics import session_minutes
from neuromancers_network.analytics.models import SessionLedger
from neuromancers_network.core.models import IntegrationSettings
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

DAILY_SECRET = "daily-webhook-secret"  # noqa: S105
WHEREBY_SECRET = "whereby-webhook-secret"  # noqa: S105
DAILY_URL = "daily_webhook"
OK = 200
FORBIDDEN = 403
DAILY_MINUTES = 30
WHEREBY_MINUTES = 45
WHEREBY_URL = "whereby_webhook"


def _sign(secret, body):
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _post(client, url_name, payload, secret, header):
    body = json.dumps(payload).encode()
    return client.post(
        reverse(url_name),
        data=body,
        content_type="application/json",
        **{header: _sign(secret, body)},
    )


def _configure(*, daily="", whereby=""):
    config = IntegrationSettings.load()
    config.daily_webhook_secret = daily
    config.whereby_webhook_secret = whereby
    config.save()


def _one_to_one(provider="daily", room_id="room-1"):
    meeting = create_meeting(peer=make_peer())
    return MeetingRequest.objects.create(
        meeting=meeting,
        support_seeker=UserFactory(),
        status=MeetingRequestStatus.PAID,
        provider=provider,
        provider_room_id=room_id,
    )


def _group(provider="whereby", room_id="room-2"):
    meeting = create_meeting(peer=make_peer())
    meeting.meeting_type = MeetingType.GROUP
    meeting.scheduled_at = timezone.now()
    meeting.duration_minutes = 60
    meeting.provider = provider
    meeting.provider_room_id = room_id
    meeting.save(validate=False)
    return meeting


DAILY_EVENT = {
    "event": "meeting.ended",
    "id": "evt_daily_1",
    "payload": {
        "room": "room-1",
        "start_ts": 1_700_000_000,
        "end_ts": 1_700_001_800,
    },
}

WHEREBY_EVENT = {
    "event": "meeting.ended",
    "id": "evt_whereby_1",
    "data": {
        "meetingId": "room-2",
        "startDate": "2026-05-01T10:00:00Z",
        "endDate": "2026-05-01T10:45:00Z",
    },
}


class TestDailyWebhook:
    def test_records_one_to_one_minutes_and_is_replay_safe(self, client):
        _configure(daily=DAILY_SECRET)
        request_row = _one_to_one()

        first = _post(
            client,
            DAILY_URL,
            DAILY_EVENT,
            DAILY_SECRET,
            "HTTP_X_WEBHOOK_SIGNATURE",
        )
        second = _post(
            client,
            DAILY_URL,
            DAILY_EVENT,
            DAILY_SECRET,
            "HTTP_X_WEBHOOK_SIGNATURE",
        )

        assert first.status_code == OK
        assert second.status_code == OK
        entry = SessionLedger.objects.get(meeting_request=request_row)
        assert entry.minutes == DAILY_MINUTES
        assert entry.provider == "daily"
        assert SessionLedger.objects.count() == 1

    def test_bad_signature_is_forbidden(self, client):
        _configure(daily=DAILY_SECRET)
        request_row = _one_to_one()

        response = client.post(
            reverse(DAILY_URL),
            data=json.dumps(DAILY_EVENT),
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE="not-valid",
        )

        assert response.status_code == FORBIDDEN
        assert not SessionLedger.objects.filter(meeting_request=request_row).exists()

    def test_missing_secret_is_forbidden(self, client):
        _configure(daily="")
        _one_to_one()

        response = _post(
            client,
            DAILY_URL,
            DAILY_EVENT,
            DAILY_SECRET,
            "HTTP_X_WEBHOOK_SIGNATURE",
        )

        assert response.status_code == FORBIDDEN
        assert not SessionLedger.objects.exists()


class TestWherebyWebhook:
    def test_records_group_minutes(self, client):
        _configure(whereby=WHEREBY_SECRET)
        meeting = _group()

        response = _post(
            client,
            WHEREBY_URL,
            WHEREBY_EVENT,
            WHEREBY_SECRET,
            "HTTP_X_WHEREBY_SIGNATURE",
        )

        assert response.status_code == OK
        entry = SessionLedger.objects.get(meeting=meeting)
        assert entry.minutes == WHEREBY_MINUTES
        assert entry.provider == "whereby"
        assert entry.seeker is None

    def test_bad_signature_is_forbidden(self, client):
        _configure(whereby=WHEREBY_SECRET)
        _group()

        response = client.post(
            reverse(WHEREBY_URL),
            data=json.dumps(WHEREBY_EVENT),
            content_type="application/json",
            HTTP_X_WHEREBY_SIGNATURE="wrong",
        )

        assert response.status_code == FORBIDDEN


class TestProviderSwitch:
    def test_minutes_are_grouped_by_provider(self, client):
        _configure(daily=DAILY_SECRET, whereby=WHEREBY_SECRET)
        _one_to_one()
        _group()

        _post(
            client,
            DAILY_URL,
            DAILY_EVENT,
            DAILY_SECRET,
            "HTTP_X_WEBHOOK_SIGNATURE",
        )
        _post(
            client,
            WHEREBY_URL,
            WHEREBY_EVENT,
            WHEREBY_SECRET,
            "HTTP_X_WHEREBY_SIGNATURE",
        )

        assert session_minutes(period=PERIOD_ALL_TIME) == {
            "daily": 30,
            "whereby": 45,
        }


class TestAttendanceWebhooks:
    def test_daily_viewer_attendance(self, client):
        _configure(daily=DAILY_SECRET)
        request_row = _one_to_one()

        response = _post(
            client,
            DAILY_URL,
            {
                "event": "participant.joined",
                "id": "evt_attendance_1",
                "payload": {
                    "room": "room-1",
                    "participant": {"is_owner": False},
                    "start_ts": 1_700_000_000,
                    "end_ts": 1_700_001_200,
                },
            },
            DAILY_SECRET,
            "HTTP_X_WEBHOOK_SIGNATURE",
        )

        assert response.status_code == OK
        request_row.refresh_from_db()
        assert request_row.viewer_attended is True
        assert request_row.host_attended is False

    def test_daily_host_attendance_without_minutes(self, client):
        _configure(daily=DAILY_SECRET)
        request_row = _one_to_one()

        response = _post(
            client,
            DAILY_URL,
            {
                "event": "participant.joined",
                "id": "evt_attendance_2",
                "payload": {
                    "room": "room-1",
                    "participant": {"is_owner": True},
                },
            },
            DAILY_SECRET,
            "HTTP_X_WEBHOOK_SIGNATURE",
        )

        assert response.status_code == OK
        request_row.refresh_from_db()
        assert request_row.host_attended is True
        assert not SessionLedger.objects.filter(
            meeting_request=request_row,
        ).exists()

    def test_whereby_group_attendance_is_idempotent(self, client):
        _configure(whereby=WHEREBY_SECRET)
        meeting = _group()
        payload = {
            "event": "participant.joined",
            "id": "evt_attendance_3",
            "data": {"meetingId": "room-2", "role": "viewer"},
        }

        _post(
            client,
            WHEREBY_URL,
            payload,
            WHEREBY_SECRET,
            "HTTP_X_WHEREBY_SIGNATURE",
        )
        _post(
            client,
            WHEREBY_URL,
            payload,
            WHEREBY_SECRET,
            "HTTP_X_WHEREBY_SIGNATURE",
        )

        meeting.refresh_from_db()
        assert meeting.viewer_attended is True
        assert meeting.host_attended is False
