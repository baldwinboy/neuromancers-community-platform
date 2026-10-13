"""Query helpers for daisIE context models and feeds."""

from __future__ import annotations

from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import BookingStatus
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import Review
from neuromancers_network.meetings.search import search_meetings
from neuromancers_network.moderation.visibility import exclude_hidden
from neuromancers_network.peers.services import eligible_peer_q


def published_meetings(request=None, page=None):
    """Published meetings from currently eligible peers (the default feed)."""
    queryset = search_meetings().filter(eligible_peer_q(prefix="peer__"))
    return exclude_hidden(queryset, getattr(request, "user", None), owner_field="peer")


def my_meetings(request=None, page=None):
    """The signed-in peer's own meetings (any status)."""
    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return Meeting.objects.none()
    return (
        Meeting.objects.filter(peer=user)
        .select_related("peer")
        .prefetch_related("languages", "countries", "tags")
    )


def published_reviews(request=None, page=None):
    """Published reviews from eligible peers, minus block-hidden parties."""
    queryset = (
        Review.objects.filter(is_published=True)
        .filter(eligible_peer_q(prefix="peer__"))
        .select_related("peer", "reviewer")
    )
    viewer = getattr(request, "user", None)
    queryset = exclude_hidden(queryset, viewer, owner_field="peer")
    return exclude_hidden(queryset, viewer, owner_field="reviewer")


def user_bookings(request=None, page=None):
    """Bookings belonging to the signed-in member."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return Booking.objects.none()
    return Booking.objects.filter(support_seeker=user).select_related("meeting")


def user_payment_history(request=None, page=None):
    """The signed-in member's payments (one row per meeting request)."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return MeetingRequest.objects.none()
    return (
        MeetingRequest.objects.filter(support_seeker=user)
        .select_related("meeting")
        .order_by("-created_at")
    )


def unpaid_bookings(request=None, page=None):
    """The signed-in member's unpaid bookings (the cart feed)."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return Booking.objects.none()
    return Booking.objects.filter(
        support_seeker=user,
        status=BookingStatus.PENDING,
    ).select_related("meeting")


def host_meetings(request=None, page=None):
    """The signed-in peer's own meetings (the host dashboard feed)."""
    return my_meetings(request=request, page=page)


def host_requests(request=None, page=None):
    """Booking requests made against the signed-in peer's meetings."""
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return MeetingRequest.objects.none()
    return (
        MeetingRequest.objects.filter(meeting__peer=user)
        .select_related("meeting", "support_seeker")
        .order_by("-created_at")
    )


def host_refunds(request=None, page=None):
    """Refund requests raised against the signed-in peer's meetings."""
    from neuromancers_network.meetings.models import RefundRequest  # noqa: PLC0415

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return RefundRequest.objects.none()
    return (
        RefundRequest.objects.filter(meeting_request__meeting__peer=user)
        .select_related("meeting_request__meeting", "meeting_request__support_seeker")
        .order_by("-created_at")
    )
