"""Query helpers for daisIE context models and feeds."""

from __future__ import annotations

from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import Review
from neuromancers_network.meetings.search import search_meetings


def published_meetings(request=None, page=None):
    """All published meetings (the default meeting feed queryset)."""
    return search_meetings()


def published_reviews(request=None, page=None):
    """Published reviews, with their peer prefetched."""
    return Review.objects.filter(is_published=True).select_related("peer", "reviewer")


def user_bookings(request=None, page=None):
    """Bookings belonging to the signed-in member."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return Booking.objects.none()
    return Booking.objects.filter(support_seeker=user).select_related("meeting")
