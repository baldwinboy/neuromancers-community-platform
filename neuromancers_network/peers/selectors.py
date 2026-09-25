"""Query helpers for daisIE context models and feeds."""

from __future__ import annotations

from neuromancers_network.peers.search import search_peers


def approved_peers(request=None, page=None):
    """Approved peer profiles (the default care-provider feed queryset)."""
    return search_peers().select_related("user")
