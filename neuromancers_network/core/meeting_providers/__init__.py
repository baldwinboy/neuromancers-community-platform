"""Pluggable meeting-room providers.

Each provider knows how to create a single ephemeral room for a booked
session and return its join URL. The active provider is chosen at runtime by
``IntegrationSettings.meeting_provider`` so it can be switched without a
deploy.
"""

from neuromancers_network.core.meeting_providers.base import MeetingProvider
from neuromancers_network.core.meeting_providers.base import RoomResult
from neuromancers_network.core.meeting_providers.registry import get_provider

__all__ = ["MeetingProvider", "RoomResult", "get_provider"]
