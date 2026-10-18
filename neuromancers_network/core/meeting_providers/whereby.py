"""Whereby implementation of the meeting-provider contract."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.cache import cache

from neuromancers_network.core.apis import configure_whereby
from neuromancers_network.core.meeting_providers.base import MeetingProvider
from neuromancers_network.core.meeting_providers.base import RoomResult

if TYPE_CHECKING:
    from datetime import datetime

HOST_LINK_CACHE_SECONDS = 60


class WherebyProvider(MeetingProvider):
    """Creates transient Whereby rooms via the vendored REST client."""

    name = "whereby"

    def create_room(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        prefix: str | None = None,
    ) -> RoomResult:
        from whereby.client import meetings as whereby_meetings  # noqa: PLC0415
        from whereby.schemas import MeetingsApplicationJson  # noqa: PLC0415

        configure_whereby()
        data = MeetingsApplicationJson(  # type: ignore[call-arg]
            end_date=end_at.isoformat(),
            start_date=start_at.isoformat(),
            room_name_prefix=prefix,
        )
        result = whereby_meetings(data=data)
        return RoomResult(
            room_url=result.room_url,
            room_id=result.meeting_id,
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
        if not is_host:
            return room_url
        cache_key = f"whereby:host-room-url:{room_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        from whereby.client import meetings__meeting_id_  # noqa: PLC0415

        configure_whereby()
        result = meetings__meeting_id_(
            meeting_id=room_id,
            fields="[hostRoomUrl]",
        )
        url = result.host_room_url or room_url
        cache.set(cache_key, url, HOST_LINK_CACHE_SECONDS)
        return url
