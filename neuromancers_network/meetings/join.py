"""Server-side join resolution for 1:1 sessions and group meetings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import BookingStatus
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType

GROUP_GUEST_STATUSES = {BookingStatus.PENDING, BookingStatus.PAID}
REQUEST_GUEST_STATUSES = {
    MeetingRequestStatus.APPROVED,
    MeetingRequestStatus.PAID,
}


@dataclass(frozen=True)
class JoinTarget:
    kind: str
    meeting: Meeting
    request: MeetingRequest | None
    start: datetime
    end: datetime
    is_host: bool
    is_guest: bool


def joining_lead() -> timedelta:
    from neuromancers_network.core.models import IntegrationSettings  # noqa: PLC0415

    minutes = IntegrationSettings.load().joining_lead_minutes or 0
    return timedelta(minutes=max(0, int(minutes)))


def target_is_open(target: JoinTarget, *, now=None) -> bool:
    now = now or timezone.now()
    return target.start - joining_lead() <= now <= target.end


def _request_target(user, request_row):
    meeting = request_row.meeting
    start = request_row.requested_start_time or meeting.scheduled_at
    duration = request_row.requested_duration_minutes or meeting.duration_minutes
    if start is None or not duration:
        return None
    is_host = meeting.peer_id == user.pk
    is_guest = request_row.support_seeker_id == user.pk
    if not (is_host or is_guest) or not request_row.can_join:
        return None
    return JoinTarget(
        kind="request",
        meeting=meeting,
        request=request_row,
        start=start,
        end=start + timedelta(minutes=duration),
        is_host=is_host,
        is_guest=is_guest,
    )


def _meeting_target(user, meeting):
    if meeting.meeting_type != MeetingType.GROUP:
        return None
    if meeting.status != MeetingStatus.PUBLISHED:
        return None
    if not meeting.scheduled_at or not meeting.duration_minutes:
        return None
    is_host = meeting.peer_id == user.pk
    is_guest = (
        Booking.objects.filter(
            meeting=meeting,
            support_seeker=user,
            status__in=GROUP_GUEST_STATUSES,
        ).exists()
        or MeetingRequest.objects.filter(
            meeting=meeting,
            support_seeker=user,
            status__in=REQUEST_GUEST_STATUSES,
        ).exists()
    )
    if not (is_host or is_guest):
        return None
    return JoinTarget(
        kind="meeting",
        meeting=meeting,
        request=None,
        start=meeting.scheduled_at,
        end=meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes),
        is_host=is_host,
        is_guest=is_guest,
    )


def resolve_join_target(user, *, meeting_pk=None, request_pk=None):
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if request_pk is not None:
        request_row = (
            MeetingRequest.objects.select_related("meeting")
            .filter(pk=request_pk)
            .first()
        )
        return _request_target(user, request_row) if request_row else None
    if meeting_pk is not None:
        meeting = Meeting.objects.filter(pk=meeting_pk).first()
        return _meeting_target(user, meeting) if meeting else None
    return None


def _room_details(target):
    if target.request is not None:
        return target.request.provider_room_id, target.request.meeting_link
    return target.meeting.provider_room_id, target.meeting.meeting_link


def _provider_name(target):
    if target.request is not None and target.request.provider:
        return target.request.provider
    return target.meeting.provider or None


def join_url_for(user, target: JoinTarget) -> str:
    if not target_is_open(target):
        message = "The join window is not open"
        raise PermissionDenied(message)
    room_id, room_url = _room_details(target)
    if not room_id or not room_url:
        message = "The meeting room is not ready"
        raise PermissionDenied(message)

    from neuromancers_network.core.meeting_providers import get_provider  # noqa: PLC0415

    provider = get_provider(_provider_name(target))
    return provider.join_url(
        room_id=room_id,
        room_url=room_url,
        user=user,
        is_host=target.is_host,
        start_at=target.start,
        end_at=target.end,
    )
