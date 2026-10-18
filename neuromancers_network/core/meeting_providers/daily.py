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
        from daily.client import create_room as daily_create_room  # noqa: PLC0415
        from daily.schemas import CreateRoomApplicationJson  # noqa: PLC0415

        configure_daily()
        data = CreateRoomApplicationJson.model_construct(
            name=_room_name(prefix),
            privacy="private",
            properties={
                "nbf": int(start_at.timestamp()),
                "exp": int((end_at + ROOM_GRACE).timestamp()),
            },
        )
        result = daily_create_room(data=data)
        return RoomResult(
            room_url=result.url,
            room_id=result.id,
            provider=self.name,
        )

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
        from daily.client import create_meeting_token  # noqa: PLC0415
        from daily.schemas import CreateMeetingTokenApplicationJson  # noqa: PLC0415

        configure_daily()
        data = CreateMeetingTokenApplicationJson.model_construct(
            properties={
                "room_name": room_id,
                "user_id": str(user.pk),
                "user_name": user.get_full_name() or user.get_username(),
                "is_owner": is_host,
                "nbf": int(start_at.timestamp()),
                "exp": int(end_at.timestamp()),
            },
        )
        token = create_meeting_token(data=data)
        separator = "&" if "?" in room_url else "?"
        return f"{room_url}{separator}t={token.token}"
