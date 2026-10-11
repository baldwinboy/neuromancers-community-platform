"""Query helpers for daisIE context models and feeds."""

from __future__ import annotations

from neuromancers_network.peers.models.availability import PeerAvailability
from neuromancers_network.peers.search import search_peers


def approved_peers(request=None, page=None):
    """Approved peer profiles (the default care-provider feed queryset)."""
    return search_peers().select_related("user")


def my_availability(request=None, page=None):
    """The signed-in peer's availability windows."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return PeerAvailability.objects.none()
    return PeerAvailability.objects.filter(peer=user)
