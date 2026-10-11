"""Daily.co implementation of the meeting-provider contract."""

from __future__ import annotations

import re
from datetime import datetime
from datetime import timedelta
from uuid import uuid4

from neuromancers_network.core.apis import configure_daily
from neuromancers_network.core.meeting_providers.base import MeetingProvider
from neuromancers_network.core.meeting_providers.base import RoomResult

# Daily deletes a room the moment its ``exp`` property is reached. Keep the
# room joinable for a short grace period after the session ends, mirroring the
# Whereby provider's post-end retention.
ROOM_GRACE = timedelta(hours=1)

# Daily room names allow only ``[a-zA-Z0-9_-]``.
_UNSAFE_NAME_CHARS = re.compile(r"[^a-zA-Z0-9_-]+")


def _room_name(prefix: str | None) -> str:
    """Build a Daily-safe, unique room name from an optional prefix."""
    suffix = uuid4().hex
    if not prefix:
        return suffix
    safe_prefix = _UNSAFE_NAME_CHARS.sub("-", prefix).strip("-")
    return f"{safe_prefix}-{suffix}" if safe_prefix else suffix


class DailyProvider(MeetingProvider):
    """Creates time-boxed Daily rooms via the vendored REST client."""

    name = "daily"

    def create_room(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        prefix: str | None = None,
    ) -> RoomResult:
        from daily.client import rooms as daily_rooms  # noqa: PLC0415
        from daily.schemas import RoomsApplicationJson  # noqa: PLC0415

        configure_daily()
        data = RoomsApplicationJson(
            name=_room_name(prefix),
            privacy="public",
            properties={
                "nbf": int(start_at.timestamp()),
                "exp": int((end_at + ROOM_GRACE).timestamp()),
            },
        )
        result = daily_rooms(data=data)
        return RoomResult(
            room_url=result.url,
            room_id=result.id,
            provider=self.name,
        )
