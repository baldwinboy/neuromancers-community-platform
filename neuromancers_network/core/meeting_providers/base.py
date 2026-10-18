"""Provider contract for meeting-room creation."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class RoomResult:
    """The outcome of creating a room with an external provider."""

    room_url: str
    room_id: str
    provider: str


class MeetingProvider(ABC):
    """Creates an ephemeral meeting room for a single booked session."""

    #: Stable identifier used in ``IntegrationSettings.meeting_provider``.
    name: str

    @abstractmethod
    def create_room(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        prefix: str | None = None,
    ) -> RoomResult:
        """Create a room and return its join URL and provider room id.

        Parameters
        ----------
        start_at, end_at
            Timezone-aware window the room should be usable for.
        prefix
            Optional human-friendly room-name prefix, when supported.
        """

    def join_url(  # noqa: PLR0913
        self,
        *,
        room_id: str,
        room_url: str,
        user,
        is_host: bool,
        start_at: datetime,
        end_at: datetime,
    ) -> str:
        """Return the role-appropriate, time-boxed join URL for a room."""
        message = f"{type(self).__name__} does not support join links"
        raise NotImplementedError(message)
