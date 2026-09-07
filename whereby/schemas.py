from __future__ import annotations

import inspect
import typing

import pydantic
from clientele.schemas import ListResponse


class Fields(ListResponse[str]):
    pass


class Meeting(pydantic.BaseModel):
    meeting_id: str = pydantic.Field(alias="meetingId")
    room_name: str | None = pydantic.Field(default=None, alias="roomName")
    room_url: str = pydantic.Field(alias="roomUrl")
    start_date: str | None = pydantic.Field(default=None, alias="startDate")
    end_date: str = pydantic.Field(alias="endDate")
    host_room_url: str | None = pydantic.Field(
        default=None, alias="hostRoomUrl",
    )
    viewer_room_url: str | None = pydantic.Field(
        default=None, alias="viewerRoomUrl",
    )

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Recording(pydantic.BaseModel):
    pass


class Transcription(pydantic.BaseModel):
    transcription_id: str = pydantic.Field(alias="transcriptionId")
    room_session_id: str = pydantic.Field(alias="roomSessionId")
    filename: str | None = None
    room_name: str = pydantic.Field(alias="roomName")
    start_date: str = pydantic.Field(alias="startDate")
    end_date: str = pydantic.Field(alias="endDate")
    state: str
    created_at: str = pydantic.Field(alias="createdAt")
    duration_in_seconds: float | None = pydantic.Field(
        default=None, alias="durationInSeconds",
    )
    type_: str = pydantic.Field(alias="type")
    storage_type: str | None = pydantic.Field(
        default=None, alias="storageType",
    )

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Summary(pydantic.BaseModel):
    pass


class Meetings200Response(pydantic.BaseModel):
    results: list[Meeting]
    cursor: str


class MeetingsApplicationJson(pydantic.BaseModel):
    end_date: str = pydantic.Field(alias="endDate")
    start_date: str | None = pydantic.Field(default=None, alias="startDate")
    is_locked: bool | None = pydantic.Field(default=None, alias="isLocked")
    room_mode: str = pydantic.Field(default="normal", alias="roomMode")
    room_name_prefix: str | None = pydantic.Field(
        default=None, alias="roomNamePrefix",
    )
    room_name_pattern: str = pydantic.Field(default="uuid", alias="roomNamePattern")
    template_type: str | None = pydantic.Field(
        default=None, alias="templateType",
    )
    recording: dict[str, typing.Any] | None = None
    live_transcription: dict[str, typing.Any] | None = pydantic.Field(
        default=None, alias="liveTranscription",
    )
    streaming: dict[str, typing.Any] | None = None
    fields: Fields | None = None

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Recordings200Response(pydantic.BaseModel):
    results: list[Recording]
    cursor: str


class RecordingsRecordingIdAccessLink200Response(pydantic.BaseModel):
    access_link: str = pydantic.Field(alias="accessLink")
    expires: int

    model_config = pydantic.ConfigDict(populate_by_name=True)


class RecordingsBulkDeleteApplicationJson(pydantic.BaseModel):
    recording_ids: list[str] = pydantic.Field(alias="recordingIds")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Transcriptions200Response(pydantic.BaseModel):
    results: list[Transcription]
    cursor: str


class Transcriptions201Response(pydantic.BaseModel):
    transcription_id: str = pydantic.Field(alias="transcriptionId")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class TranscriptionsApplicationJson(pydantic.BaseModel):
    recording_id: str = pydantic.Field(alias="recordingId")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class TranscriptionsTranscriptionIdAccessLink200Response(pydantic.BaseModel):
    access_link: str = pydantic.Field(alias="accessLink")
    expires: int

    model_config = pydantic.ConfigDict(populate_by_name=True)


class TranscriptionsBulkDeleteApplicationJson(pydantic.BaseModel):
    transcription_ids: list[str] = pydantic.Field(alias="transcriptionIds")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Summaries200Response(pydantic.BaseModel):
    results: list[Summary]
    cursor: str


class Summaries201Response(pydantic.BaseModel):
    summary_id: str = pydantic.Field(alias="summaryId")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class SummariesApplicationJson(pydantic.BaseModel):
    transcription_id: str = pydantic.Field(alias="transcriptionId")
    template: str | None = None

    model_config = pydantic.ConfigDict(populate_by_name=True)


class RoomsRoomNameThemeTokensApplicationJson(pydantic.BaseModel):
    tokens: dict[str, typing.Any]
    tokens_preset: str = pydantic.Field(alias="tokensPreset")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class RoomsRoomNameThemeLogoApplicationJson(pydantic.BaseModel):
    theme: str


class RoomsRoomNameThemeLogoApplicationJson(pydantic.BaseModel):
    theme: str


class RoomsRoomNameThemeRoomBackgroundApplicationJson(pydantic.BaseModel):
    palette: str
    theme: str


class RoomsRoomNameThemeRoomBackgroundApplicationJson(pydantic.BaseModel):
    palette: str
    theme: str


class RoomsRoomNameThemeRoomKnockPageBackgroundApplicationJson(pydantic.BaseModel):
    palette: str
    theme: str


class RoomsRoomNameThemeRoomKnockPageBackgroundApplicationJson(pydantic.BaseModel):
    palette: str
    theme: str


class InsightsRooms200Response(pydantic.BaseModel):
    cursor: str
    results: list[dict[str, typing.Any]]


class InsightsRoomSessions200Response(pydantic.BaseModel):
    cursor: str
    results: list[dict[str, typing.Any]]


class InsightsParticipants200Response(pydantic.BaseModel):
    cursor: str
    results: list[dict[str, typing.Any]]


class InsightsParticipant200Response(ListResponse[dict[str, typing.Any]]):
    pass


def get_subclasses_from_same_file() -> list[type[pydantic.BaseModel]]:
    """
    Due to how Python declares classes in a module,
    we need to update_forward_refs for all the schemas generated
    here in the situation where there are nested classes.
    """
    calling_frame = inspect.currentframe()
    if not calling_frame:
        return []
    calling_frame = calling_frame.f_back
    module = inspect.getmodule(calling_frame)

    subclasses = []
    for _, c in inspect.getmembers(module):
        if (
            inspect.isclass(c)
            and issubclass(c, pydantic.BaseModel)
            and c != pydantic.BaseModel
        ):
            subclasses.append(c)

    return subclasses


subclasses: list[type[pydantic.BaseModel]] = get_subclasses_from_same_file()
for c in subclasses:
    c.model_rebuild()
