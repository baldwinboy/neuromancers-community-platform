"""Bookmark toggle actions."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated


def _toggle_response(request, *, bookmarked: bool) -> HttpResponse:
    if getattr(request, "htmx", False):
        return HttpResponse(
            "Saved" if bookmarked else "Removed",
            content_type="text/plain",
        )
    return redirect_back(request)


def toggle_peer(request, data):
    """Add or remove a care provider from the member's bookmarks."""
    from neuromancers_network.peers.models import PeerProfile  # noqa: PLC0415
    from neuromancers_network.peers.models import PeersBookmark  # noqa: PLC0415
    from neuromancers_network.peers.services import is_eligible_peer  # noqa: PLC0415

    user = require_authenticated(request)
    pk = data.get("peer") or data.get("peer_pk") or data.get("target")
    profile = (
        PeerProfile.objects.select_related("user")
        .filter(pk=pk, is_approved=True)
        .first()
    )
    if profile is None or not is_eligible_peer(profile.user):
        message = "This care provider cannot be bookmarked"
        raise PermissionDenied(message)

    bookmark, _created = PeersBookmark.objects.get_or_create(user=user)
    if bookmark.peers.filter(pk=profile.pk).exists():
        bookmark.peers.remove(profile)
        return _toggle_response(request, bookmarked=False)
    bookmark.peers.add(profile)
    return _toggle_response(request, bookmarked=True)


def toggle_meeting(request, data):
    """Add or remove a meeting from the member's bookmarks."""
    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingsBookmark  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingStatus  # noqa: PLC0415
    from neuromancers_network.peers.services import is_eligible_peer  # noqa: PLC0415

    user = require_authenticated(request)
    pk = data.get("meeting") or data.get("meeting_pk") or data.get("target")
    meeting = (
        Meeting.objects.select_related("peer")
        .filter(pk=pk, status=MeetingStatus.PUBLISHED)
        .first()
    )
    if meeting is None or not is_eligible_peer(meeting.peer):
        message = "This meeting cannot be bookmarked"
        raise PermissionDenied(message)

    bookmark, _created = MeetingsBookmark.objects.get_or_create(user=user)
    if bookmark.meetings.filter(pk=meeting.pk).exists():
        bookmark.meetings.remove(meeting)
        return _toggle_response(request, bookmarked=False)
    bookmark.meetings.add(meeting)
    return _toggle_response(request, bookmarked=True)
