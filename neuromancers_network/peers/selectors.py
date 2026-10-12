"""Query helpers for daisIE context models and feeds."""

from __future__ import annotations

from neuromancers_network.peers.models.availability import PeerAvailability
from neuromancers_network.peers.search import search_peers
from neuromancers_network.peers.services import eligible_peer_q


def approved_peers(request=None, page=None):
    """Currently eligible peer profiles (the default care-provider feed)."""
    return (
        search_peers().select_related("user").filter(eligible_peer_q(prefix="user__"))
    )


def my_availability(request=None, page=None):
    """The signed-in peer's availability windows."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return PeerAvailability.objects.none()
    return PeerAvailability.objects.filter(peer=user)


def _calendar_owner(request):
    from neuromancers_network.peers.models.profile import PeerProfile  # noqa: PLC0415

    path_params = getattr(request, "daisie_path_params", None) or {}
    pk = path_params.get("pk")
    if pk:
        profile = PeerProfile.objects.filter(pk=pk).select_related("user").first()
        if profile is not None:
            return profile.user
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


def peer_calendar_events(request=None, page=None):
    """Viewer-aware calendar events for a peer (titles redacted by privacy)."""
    from django.db.models import Case  # noqa: PLC0415
    from django.db.models import CharField  # noqa: PLC0415
    from django.db.models import F  # noqa: PLC0415
    from django.db.models import Value  # noqa: PLC0415
    from django.db.models import When  # noqa: PLC0415

    from neuromancers_network.peers.models.calendar_event import (  # noqa: PLC0415
        CalendarEvent,
    )
    from neuromancers_network.peers.models.choices import (  # noqa: PLC0415
        CalendarEventKind,
    )

    owner = _calendar_owner(request)
    if owner is None:
        return CalendarEvent.objects.none()

    queryset = CalendarEvent.objects.filter(owner=owner)
    viewer = getattr(request, "user", None)
    viewer_id = getattr(viewer, "pk", None)
    if viewer_id == owner.pk:
        return queryset

    profile = getattr(owner, "user_profile", None)
    if profile is None or not profile.show_calendar:
        return CalendarEvent.objects.none()

    whens = []
    if profile.show_group_meeting_details:
        whens.append(When(kind=CalendarEventKind.GROUP, then=F("title")))
    if profile.show_peer_meeting_details:
        whens.append(When(kind=CalendarEventKind.ONE_TO_ONE, then=F("title")))
    else:
        whens.append(
            When(
                kind=CalendarEventKind.ONE_TO_ONE,
                participant_ids__contains=[viewer_id],
                then=F("title"),
            ),
        )
    whens.append(When(kind=CalendarEventKind.AVAILABLE, then=Value("Available")))
    return queryset.annotate(
        display_title=Case(*whens, default=Value(""), output_field=CharField()),
    )
