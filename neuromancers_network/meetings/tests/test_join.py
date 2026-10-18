from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from neuromancers_network.core.audience import is_joining_upcoming_meeting_as_guest
from neuromancers_network.core.audience import is_joining_upcoming_meeting_as_host
from neuromancers_network.core.meeting_providers.daily import DailyProvider
from neuromancers_network.core.models import IntegrationSettings
from neuromancers_network.meetings.join import join_url_for
from neuromancers_network.meetings.join import resolve_join_target
from neuromancers_network.meetings.join import target_is_open
from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import BookingStatus
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

WHEREBY_ROOM_ID = "room-1"
WHEREBY_ROOM_URL = "https://whereby.example/room-1"


def _lead(minutes=30):
    config = IntegrationSettings.load()
    config.joining_lead_minutes = minutes
    config.save()


def _one_to_one(offset_minutes=15):
    peer = make_peer()
    seeker = UserFactory()
    meeting = create_meeting(peer=peer)
    start = timezone.now() + timedelta(minutes=offset_minutes)
    booking = create_booking(
        meeting=meeting,
        seeker=seeker,
        sessions=[
            {
                "requested_start_time": start,
                "requested_duration_minutes": 60,
            },
        ],
    )
    request_row = booking.sessions.first()
    request_row.status = MeetingRequestStatus.PAID
    request_row.provider = "whereby"
    request_row.provider_room_id = WHEREBY_ROOM_ID
    request_row.meeting_link = WHEREBY_ROOM_URL
    request_row.save(validate=False)
    return request_row, peer, seeker


def _group(offset_minutes=15):
    peer = make_peer()
    seeker = UserFactory()
    meeting = create_meeting(peer=peer)
    meeting.meeting_type = MeetingType.GROUP
    meeting.scheduled_at = timezone.now() + timedelta(minutes=offset_minutes)
    meeting.duration_minutes = 60
    meeting.provider = "whereby"
    meeting.provider_room_id = WHEREBY_ROOM_ID
    meeting.meeting_link = WHEREBY_ROOM_URL
    meeting.save(validate=False)
    Booking.objects.create(
        meeting=meeting,
        support_seeker=seeker,
        status=BookingStatus.PAID,
    )
    return meeting, peer, seeker


class TestJoinTargets:
    def test_one_to_one_roles(self):
        _lead()
        request_row, peer, seeker = _one_to_one()

        host = resolve_join_target(peer, request_pk=request_row.pk)
        guest = resolve_join_target(seeker, request_pk=request_row.pk)

        assert host.is_host
        assert not host.is_guest
        assert guest.is_guest
        assert not guest.is_host
        assert resolve_join_target(UserFactory(), request_pk=request_row.pk) is None

    def test_group_roles(self):
        _lead()
        meeting, peer, seeker = _group()

        host = resolve_join_target(peer, meeting_pk=meeting.pk)
        guest = resolve_join_target(seeker, meeting_pk=meeting.pk)

        assert host.is_host
        assert guest.is_guest
        assert resolve_join_target(UserFactory(), meeting_pk=meeting.pk) is None

    def test_group_requires_published(self):
        _lead()
        meeting, peer, _seeker = _group()
        meeting.status = MeetingStatus.DRAFT
        meeting.save(validate=False)

        assert resolve_join_target(peer, meeting_pk=meeting.pk) is None

    def test_window_open_and_closed(self):
        _lead(minutes=30)
        request_row, peer, _seeker = _one_to_one(offset_minutes=15)
        target = resolve_join_target(peer, request_pk=request_row.pk)

        assert target_is_open(target) is True

        MeetingRequest.objects.filter(pk=request_row.pk).update(
            requested_start_time=timezone.now() - timedelta(hours=2),
        )
        request_row.refresh_from_db()
        target = resolve_join_target(peer, request_pk=request_row.pk)
        assert target_is_open(target) is False


class TestJoinLinks:
    def test_whereby_guest_uses_the_stored_room_url(self):
        _lead()
        request_row, _peer, seeker = _one_to_one()
        target = resolve_join_target(seeker, request_pk=request_row.pk)

        assert join_url_for(seeker, target) == WHEREBY_ROOM_URL

    def test_whereby_host_fetches_the_host_room_url(self):
        _lead()
        cache.clear()
        request_row, peer, _seeker = _one_to_one()
        target = resolve_join_target(peer, request_pk=request_row.pk)

        with patch(
            "whereby.client.meetings__meeting_id_",
            return_value=SimpleNamespace(
                host_room_url="https://whereby.example/host-room-1",
            ),
        ) as fetch:
            url = join_url_for(peer, target)

        assert url == "https://whereby.example/host-room-1"
        fetch.assert_called_once_with(
            meeting_id=WHEREBY_ROOM_ID,
            fields="[hostRoomUrl]",
        )

    def test_daily_room_is_private(self):
        start = timezone.now()
        with (
            patch("daily.client.create_room") as create_room,
            patch(
                "neuromancers_network.core.meeting_providers.daily.configure_daily",
            ),
        ):
            create_room.return_value = SimpleNamespace(
                url=WHEREBY_ROOM_URL,
                id=WHEREBY_ROOM_ID,
            )
            result = DailyProvider().create_room(
                start_at=start,
                end_at=start + timedelta(hours=1),
            )

        assert create_room.call_args.kwargs["data"].privacy == "private"
        assert result.provider == "daily"

    def test_daily_join_link_carries_a_token(self):
        with (
            patch("daily.client.create_meeting_token") as token_create,
            patch(
                "neuromancers_network.core.meeting_providers.daily.configure_daily",
            ),
        ):
            token_create.return_value = SimpleNamespace(token="tok-123")  # noqa: S106
            url = DailyProvider().join_url(
                room_id=WHEREBY_ROOM_ID,
                room_url=WHEREBY_ROOM_URL,
                user=UserFactory(),
                is_host=False,
                start_at=timezone.now(),
                end_at=timezone.now() + timedelta(hours=1),
            )

        assert url == f"{WHEREBY_ROOM_URL}?t=tok-123"


class TestJoinEndpoint:
    def test_participant_is_redirected(self, client):
        _lead()
        request_row, _peer, seeker = _one_to_one()
        client.force_login(seeker)

        response = client.get(
            reverse("meetings:join_meeting", args=["request", request_row.pk]),
        )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == WHEREBY_ROOM_URL

    def test_stranger_is_denied(self, client):
        _lead()
        request_row, _peer, _seeker = _one_to_one()
        client.force_login(UserFactory())

        response = client.get(
            reverse("meetings:join_meeting", args=["request", request_row.pk]),
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_closed_window_is_denied(self, client):
        _lead(minutes=5)
        request_row, _peer, seeker = _one_to_one(offset_minutes=30)
        client.force_login(seeker)

        response = client.get(
            reverse("meetings:join_meeting", args=["request", request_row.pk]),
        )

        assert response.status_code == HTTPStatus.FORBIDDEN


class TestAudienceRules:
    def _request(self, user, *, meeting_pk=None, request_pk=None):
        request = RequestFactory().get("/")
        request.user = user
        request.daisie_path_params = {}
        if meeting_pk is not None:
            request.daisie_path_params["meeting_pk"] = meeting_pk
        if request_pk is not None:
            request.daisie_path_params["meeting_request_pk"] = request_pk
        return request

    def test_host_and_guest_rules(self):
        _lead()
        request_row, peer, seeker = _one_to_one()

        assert is_joining_upcoming_meeting_as_host(
            self._request(peer, request_pk=request_row.pk),
        )
        assert is_joining_upcoming_meeting_as_guest(
            self._request(seeker, request_pk=request_row.pk),
        )
        assert not is_joining_upcoming_meeting_as_host(
            self._request(seeker, request_pk=request_row.pk),
        )


class TestProviderRecorded:
    def test_request_room_records_provider(self):
        peer = make_peer()
        seeker = UserFactory()
        meeting = create_meeting(peer=peer)
        start = timezone.now() + timedelta(minutes=15)
        booking = create_booking(
            meeting=meeting,
            seeker=seeker,
            sessions=[
                {
                    "requested_start_time": start,
                    "requested_duration_minutes": 60,
                },
            ],
        )
        request_row = booking.sessions.first()

        with patch(
            "neuromancers_network.core.meeting_providers.get_provider",
        ) as get_provider:
            get_provider.return_value.create_room.return_value = SimpleNamespace(
                room_url="https://daily.example/room",
                room_id="room-9",
                provider="daily",
            )
            request_row.populate_meeting_link()

        request_row.refresh_from_db()
        assert request_row.provider == "daily"
        assert request_row.provider_room_id == "room-9"
