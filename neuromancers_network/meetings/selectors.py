"""Query helpers for daisIE context models and feeds."""

from __future__ import annotations

from django.db.models import Q

from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import BookingStatus
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import RefundRequest
from neuromancers_network.meetings.models import Review
from neuromancers_network.meetings.models import ReviewStatus
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
        Review.objects.filter(status=ReviewStatus.PUBLISHED)
        .filter(eligible_peer_q(prefix="peer__"))
        .select_related("peer", "reviewer")
    )
    viewer = getattr(request, "user", None)
    queryset = exclude_hidden(queryset, viewer, owner_field="peer")
    return exclude_hidden(queryset, viewer, owner_field="reviewer")


def _viewer(request):
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return user


def _apply_common_filters(
    queryset,
    *,
    status=None,
    created_after=None,
    created_before=None,
):
    if status is not None:
        queryset = queryset.filter(status=status)
    if created_after is not None:
        queryset = queryset.filter(created_at__gte=created_after)
    if created_before is not None:
        queryset = queryset.filter(created_at__lte=created_before)
    return queryset


def viewable_bookings(  # noqa: PLR0913
    request=None,
    page=None,
    *,
    status=None,
    created_after=None,
    created_before=None,
    session_after=None,
    session_before=None,
):
    """Bookings where the signed-in member is the seeker or the host."""
    user = _viewer(request)
    if user is None:
        return Booking.objects.none()
    queryset = (
        Booking.objects.filter(
            Q(support_seeker=user) | Q(meeting__peer=user),
        )
        .select_related("meeting", "meeting__peer", "support_seeker")
        .order_by("-created_at")
    )
    queryset = _apply_common_filters(
        queryset,
        status=status,
        created_after=created_after,
        created_before=created_before,
    )
    if session_after is not None:
        queryset = queryset.filter(
            sessions__requested_start_time__gte=session_after,
        )
    if session_before is not None:
        queryset = queryset.filter(
            sessions__requested_start_time__lte=session_before,
        )
    return queryset.distinct()


def host_bookings(
    request=None,
    page=None,
    *,
    status=None,
    created_after=None,
    created_before=None,
):
    """Bookings purchased against the signed-in peer's meetings."""
    user = _viewer(request)
    if user is None:
        return Booking.objects.none()
    queryset = (
        Booking.objects.filter(meeting__peer=user)
        .select_related("meeting", "meeting__peer", "support_seeker")
        .order_by("-created_at")
    )
    return _apply_common_filters(
        queryset,
        status=status,
        created_after=created_after,
        created_before=created_before,
    )


def booking_for_viewer(request, pk):
    """Return *pk*'s booking when the viewer is a participant, else ``None``."""
    if pk in (None, ""):
        return None
    return viewable_bookings(request).filter(pk=pk).first()


def viewable_refunds(  # noqa: PLR0913
    request=None,
    page=None,
    *,
    status=None,
    created_after=None,
    created_before=None,
    session_after=None,
    session_before=None,
):
    """Refund requests where the signed-in member is the seeker or the host."""
    user = _viewer(request)
    if user is None:
        return RefundRequest.objects.none()
    queryset = (
        RefundRequest.objects.filter(
            Q(meeting_request__support_seeker=user)
            | Q(meeting_request__meeting__peer=user),
        )
        .select_related(
            "meeting_request__meeting",
            "meeting_request__support_seeker",
        )
        .order_by("-created_at")
    )
    queryset = _apply_common_filters(
        queryset,
        status=status,
        created_after=created_after,
        created_before=created_before,
    )
    if session_after is not None:
        queryset = queryset.filter(
            meeting_request__requested_start_time__gte=session_after,
        )
    if session_before is not None:
        queryset = queryset.filter(
            meeting_request__requested_start_time__lte=session_before,
        )
    return queryset.distinct()


def refund_for_viewer(request, pk):
    """Return *pk*'s refund request when the viewer participates, else ``None``."""
    if pk in (None, ""):
        return None
    return viewable_refunds(request).filter(pk=pk).first()


def user_requests(request=None, page=None, *, status=None, **filters):
    """Meeting requests raised by the signed-in seeker."""
    user = _viewer(request)
    if user is None:
        return MeetingRequest.objects.none()
    queryset = (
        MeetingRequest.objects.filter(support_seeker=user)
        .select_related("meeting", "meeting__peer")
        .order_by("-created_at")
    )
    return _apply_common_filters(queryset, status=status, **filters)


def user_refunds(request=None, page=None, *, status=None, **filters):
    """Refund requests raised by the signed-in seeker."""
    user = _viewer(request)
    if user is None:
        return RefundRequest.objects.none()
    queryset = (
        RefundRequest.objects.filter(meeting_request__support_seeker=user)
        .select_related("meeting_request__meeting")
        .order_by("-created_at")
    )
    return _apply_common_filters(queryset, status=status, **filters)


def bookings_for_context(request=None, page=None):
    """Booking context binding (participant-scoped)."""
    return viewable_bookings(request=request, page=page)


def refunds_for_context(request=None, page=None):
    """Refund-request context binding (participant-scoped)."""
    return viewable_refunds(request=request, page=page)


def meeting_requests_for_context(request=None, page=None):
    """Meeting-request context binding (seeker or host)."""
    user = _viewer(request)
    if user is None:
        return MeetingRequest.objects.none()
    return (
        MeetingRequest.objects.filter(
            Q(support_seeker=user) | Q(meeting__peer=user),
        )
        .select_related("meeting", "meeting__peer", "support_seeker")
        .order_by("-created_at")
    )


def user_bookings(request=None, page=None):
    """Bookings belonging to the signed-in member."""
    user = _viewer(request)
    if user is None:
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
