from __future__ import annotations

import inspect
import typing
import decimal
import enum

import pydantic

from clientele.schemas import ListResponse  # noqa

class Geo(pydantic.BaseModel):
    pass

class RtmpGeo(pydantic.BaseModel):
    pass

class DisableRtmpGeoFallback(pydantic.BaseModel):
    pass

class EnableTerseLogging(pydantic.BaseModel):
    pass

class EnableTranscriptionStorage(pydantic.BaseModel):
    pass

class TranscriptionBucket(pydantic.BaseModel):
    storage_provider: str = 'aws'
    bucket_name: str
    bucket_region: str
    namespace: str
    assume_role_arn: str
    allow_api_access: bool


class RecordingsTemplate(pydantic.BaseModel):
    pass

class TranscriptionTemplate(pydantic.BaseModel):
    pass

class EnableMeshSfu(pydantic.BaseModel):
    pass

class SfuSwitchover(pydantic.BaseModel):
    pass

class EnableAdaptiveSimulcast(pydantic.BaseModel):
    pass

class EnforceUniqueUserIds(pydantic.BaseModel):
    pass

class RecordingsBucket(pydantic.BaseModel):
    storage_provider: str = 'aws'
    bucket_name: str
    bucket_region: str
    namespace: str
    assume_role_arn: str
    allow_api_access: bool
    allow_streaming_from_bucket: bool


class SignedRecordingLink(pydantic.BaseModel):
    pass

class SignedTranscriptLink(pydantic.BaseModel):
    pass

class Permissions(pydantic.BaseModel):
    has_presence: bool = pydantic.Field(alias="hasPresence")
    can_send: bool | list[str] = pydantic.Field(alias="canSend")
    can_receive: dict[str, typing.Any] = pydantic.Field(alias="canReceive")
    can_admin: bool | list[str] = pydantic.Field(alias="canAdmin")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class PinlessDialin(ListResponse[dict[str, typing.Any]]):
    pass

class PinDialin(ListResponse[dict[str, typing.Any]]):
    pass

class Domain(pydantic.BaseModel):
    properties: dict[str, typing.Any]


class EnableMultipartyAdaptiveSimulcast(pydantic.BaseModel):
    pass

class AutoTranscriptionSettings(pydantic.BaseModel):
    pass

class RoomProperties(pydantic.BaseModel):
    nbf: int
    exp: int
    max_participants: int = 200
    enable_people_ui: bool
    enable_cpu_warning_notifications: bool
    enable_pip_ui: bool
    enable_emoji_reactions: bool
    enable_hand_raising: bool
    enable_prejoin_ui: bool
    enable_live_captions_ui: bool
    enable_network_ui: bool
    enable_noise_cancellation_ui: bool
    enable_breakout_rooms: bool
    enable_knocking: bool
    enable_screenshare: bool = True
    enable_video_processing_ui: bool = True
    enable_chat: bool = False
    enable_shared_chat_history: bool = True
    start_video_off: bool = False
    start_audio_off: bool = False
    enable_recording: str | list[str]
    enable_raw_tracks_transcoded_audio: str
    eject_at_room_exp: bool = False
    eject_after_elapsed: int
    enable_advanced_chat: bool = False
    enable_hidden_participants: bool = False
    enable_mesh_sfu: "EnableMeshSfu"
    sfu_switchover: "SfuSwitchover"
    enable_adaptive_simulcast: "EnableAdaptiveSimulcast"
    enable_multiparty_adaptive_simulcast: "EnableMultipartyAdaptiveSimulcast"
    enforce_unique_user_ids: "EnforceUniqueUserIds"
    experimental_optimize_large_calls: bool
    lang: str = 'en'
    meeting_join_hook: str
    geo: "Geo"
    rtmp_geo: "RtmpGeo"
    disable_rtmp_geo_fallback: "DisableRtmpGeoFallback"
    recordings_bucket: "RecordingsBucket"
    enable_terse_logging: "EnableTerseLogging"
    auto_transcription_settings: "AutoTranscriptionSettings"
    enable_transcription_storage: "EnableTranscriptionStorage"
    transcription_bucket: "TranscriptionBucket"
    recordings_template: "RecordingsTemplate"
    transcription_template: "TranscriptionTemplate"
    enable_dialout: bool = False
    dialout_config: dict[str, typing.Any]
    streaming_endpoints: list[dict[str, typing.Any]]
    permissions: "Permissions"
    sip: dict[str, typing.Any]


class RoomsRoomNameGetRes(pydantic.BaseModel):
    id: str
    name: str
    api_created: bool = True
    privacy: str
    url: str
    created_at: str
    config: dict[str, typing.Any]


class RoomsRoomNamePresenceGetRes(pydantic.BaseModel):
    total_count: int
    data: list[dict[str, typing.Any]]


class DailyStreamingDefaultLayoutConfig(pydantic.BaseModel):
    preset: str
    max_cam_streams: typing.Optional[float] = None


class DailyStreamingSingleParticipantLayoutConfig(pydantic.BaseModel):
    preset: str
    session_id: str


class DailyStreamingActiveParticipantLayoutConfig(pydantic.BaseModel):
    preset: str


class DailyStreamingPortraitLayoutVariant(str, enum.Enum):
    VERTICAL = "vertical"
    INSET = "inset"


class DailyStreamingPortraitLayoutConfig(pydantic.BaseModel):
    preset: str
    variant: typing.Optional["DailyStreamingPortraitLayoutVariant"] = None
    max_cam_streams: typing.Optional[float] = None


class DailyStreamingCustomLayoutConfig(pydantic.BaseModel):
    preset: str
    composition_id: str
    composition_params: typing.Optional[dict[str, typing.Any]] = None
    session_assets: typing.Optional[dict[str, typing.Any]] = None

DailyStreamingLayoutConfig = typing.Annotated[DailyStreamingDefaultLayoutConfig | DailyStreamingSingleParticipantLayoutConfig | DailyStreamingActiveParticipantLayoutConfig | DailyStreamingPortraitLayoutConfig | DailyStreamingCustomLayoutConfig, pydantic.Field(discriminator="preset")]

class RecordingStreamingOptions(pydantic.BaseModel):
    width: float
    height: float
    fps: float
    video_bitrate: float = pydantic.Field(alias="videoBitrate")
    audio_bitrate: float = pydantic.Field(alias="audioBitrate")
    min_idle_time_out: float = pydantic.Field(alias="minIdleTimeOut")
    max_duration: float = pydantic.Field(alias="maxDuration")
    background_color: str = pydantic.Field(alias="backgroundColor")
    instance_id: str = pydantic.Field(alias="instanceId")
    type_: str = pydantic.Field(default='cloud', alias="type")
    layout: "DailyStreamingLayoutConfig"
    data_outputs: list[str] = pydantic.Field(alias="dataOutputs")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DailyStreamingOptions(pydantic.BaseModel):
    width: float
    height: float
    fps: float
    video_bitrate: float = pydantic.Field(alias="videoBitrate")
    audio_bitrate: float = pydantic.Field(alias="audioBitrate")
    min_idle_time_out: float = pydantic.Field(alias="minIdleTimeOut")
    max_duration: float = pydantic.Field(alias="maxDuration")
    background_color: str = pydantic.Field(alias="backgroundColor")
    instance_id: str = pydantic.Field(alias="instanceId")
    type_: str = pydantic.Field(alias="type")
    layout: "DailyStreamingLayoutConfig"

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DailyStreamingEndpoint(pydantic.BaseModel):
    endpoint: str


class DailyLiveStreamingOptions(pydantic.BaseModel):
    width: float
    height: float
    fps: float
    video_bitrate: float = pydantic.Field(alias="videoBitrate")
    audio_bitrate: float = pydantic.Field(alias="audioBitrate")
    min_idle_time_out: float = pydantic.Field(alias="minIdleTimeOut")
    max_duration: float = pydantic.Field(alias="maxDuration")
    background_color: str = pydantic.Field(alias="backgroundColor")
    instance_id: str = pydantic.Field(alias="instanceId")
    type_: str = pydantic.Field(default='cloud', alias="type")
    layout: "DailyStreamingLayoutConfig"
    data_outputs: list[str] = pydantic.Field(alias="dataOutputs")
    rtmp_url: str | list[str] = pydantic.Field(alias="rtmpUrl")
    endpoints: list["DailyStreamingEndpoint"]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DailyLiveStreamingEndpointsOptions(pydantic.BaseModel):
    endpoints: list["DailyStreamingEndpoint"]
    instance_id: typing.Optional[str] = pydantic.Field(default=None, alias="instanceId")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class TranscriptionProperties(pydantic.BaseModel):
    language: str
    model: str
    tier: str
    profanity_filter: bool
    punctuate: bool
    endpointing: float | bool
    redact: bool | list[str] | list[bool]
    extra: dict[str, typing.Any]
    include_raw_response: bool = pydantic.Field(alias="includeRawResponse")
    instance_id: str = pydantic.Field(alias="instanceId")
    participants: list[str]
    transcription_geo: str = 'global'

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialoutProperties(pydantic.BaseModel):
    sip_uri: str = pydantic.Field(alias="sipUri")
    phone_number: str = pydantic.Field(alias="phoneNumber")
    extension: str
    wait_before_extension_dial_sec: int = pydantic.Field(default=0, alias="waitBeforeExtensionDialSec")
    display_name: str = pydantic.Field(alias="displayName")
    user_id: str = pydantic.Field(alias="userId")
    caller_id: str = pydantic.Field(alias="callerId")
    video: bool
    video_settings: dict[str, typing.Any] = pydantic.Field(alias="videoSettings")
    codecs: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class Properties(pydantic.BaseModel):
    room_name: str
    eject_at_token_exp: bool = False
    eject_after_elapsed: int
    nbf: int
    exp: int
    is_owner: bool = False
    user_name: str
    user_id: str
    enable_screenshare: bool = True
    start_video_off: bool = False
    start_audio_off: bool = False
    enable_recording: str | list[str]
    enable_prejoin_ui: bool
    enable_live_captions_ui: bool
    enable_recording_ui: bool
    enable_terse_logging: "EnableTerseLogging"
    knocking: bool = False
    start_cloud_recording: bool = False
    start_cloud_recording_opts: dict[str, typing.Any]
    auto_start_transcription: bool = False
    close_tab_on_exit: bool = False
    redirect_on_meeting_exit: str
    lang: str = 'en'
    permissions: "Permissions"


class DomainDialinConfigCreateReq(pydantic.BaseModel):
    type_: str = pydantic.Field(alias="type")
    phone_number: str
    name_prefix: typing.Optional[str] = None
    hmac: typing.Optional[str] = None
    room_creation_api: typing.Optional[str] = None
    hold_music_url: typing.Optional[str] = None
    timeout_config: typing.Optional[dict[str, typing.Any]] = None
    ivr_greeting: typing.Optional[dict[str, typing.Any]] = None

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DomainDialinConfigInfoRes(pydantic.BaseModel):
    id: str
    type_: str = pydantic.Field(alias="type")
    config: "DomainDialinConfigCreateReq"

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DomainDialinConfigUpdateReq(pydantic.BaseModel):
    phone_number: str
    name_prefix: str
    hmac: str
    room_creation_api: str
    hold_music_url: str
    timeout_config: dict[str, typing.Any]
    ivr_greeting: dict[str, typing.Any]


class Webhook(pydantic.BaseModel):
    uuid: typing.Optional[str] = None
    url: str
    hmac: typing.Optional[str] = None
    basic_auth: typing.Optional[str] = pydantic.Field(default=None, alias="basicAuth")
    retry_type: typing.Optional[str] = pydantic.Field(default=None, alias="retryType")
    event_types: typing.Optional[list[str]] = pydantic.Field(default=None, alias="eventTypes")
    state: typing.Optional[str] = None
    failed_count: typing.Optional[float] = pydantic.Field(default=None, alias="failedCount")
    last_moment_pushed: typing.Optional[str] = pydantic.Field(default=None, alias="lastMomentPushed")
    domain_id: typing.Optional[str] = pydantic.Field(default=None, alias="domainId")
    created_at: typing.Optional[str] = pydantic.Field(default=None, alias="createdAt")
    updated_at: typing.Optional[str] = pydantic.Field(default=None, alias="updatedAt")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class PostWebhook(pydantic.BaseModel):
    url: str
    basic_auth: str = pydantic.Field(alias="basicAuth")
    retry_type: str = pydantic.Field(alias="retryType")
    event_types: list[str] = pydantic.Field(alias="eventTypes")
    hmac: str

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class TranscriptReadyToDownload(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    id: str
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class TranscriptStarted(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    id: str
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class TranscriptError(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    id: str
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RecordingReadyToDownload(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RecordingStarted(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RecordingError(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class StreamingStarted(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class StreamingUpdated(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class StreamingEnded(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class StreamingError(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class StreamingWarning(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ParticipantJoined(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ParticipantLeft(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class WaitingParticipantJoined(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class WaitingParticipantLeft(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MeetingStarted(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MeetingEnded(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class BatchProcessorJobFinished(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class BatchProcessorError(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class CalltransferTriggered(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class CalltransferInitiated(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class CalltransferAnswered(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class CalltransferCompleted(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialoutConnected(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialoutAnswered(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialoutStopped(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialoutWarning(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialoutError(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialinReady(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialinConnected(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialinStopped(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialinWarning(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DialinError(pydantic.BaseModel):
    version: str
    type_: str = pydantic.Field(alias="type")
    event_ts: float
    payload: dict[str, typing.Any]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class UpdateWebhook(pydantic.BaseModel):
    url: str
    basic_auth: str = pydantic.Field(alias="basicAuth")
    retry_type: str = pydantic.Field(alias="retryType")
    event_types: list[str] = pydantic.Field(alias="eventTypes")
    hmac: str

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MeetingsMeetingGetRes(pydantic.BaseModel):
    id: str
    room: str
    start_time: int
    duration: int
    ongoing: bool
    max_participants: int


class MeetingParticipantsGetRes(pydantic.BaseModel):
    data: list[dict[str, typing.Any]]


class ListSipTrunks200Response(pydantic.BaseModel):
    total_count: int
    data: list[dict[str, typing.Any]]


class CreateSipTrunk200Response(pydantic.BaseModel):
    id: str
    description: str
    trunk_name: str
    sip_uri: str
    enabled: bool
    config: dict[str, typing.Any]


class CreateSipTrunkApplicationJson(pydantic.BaseModel):
    trunk_name: str
    description: typing.Optional[str] = None
    room_template: dict[str, typing.Any]
    notification: dict[str, typing.Any]
    trunk_config: typing.Optional[dict[str, typing.Any]] = None
    enabled: bool = True


class GetSipTrunk200Response(pydantic.BaseModel):
    id: str
    description: str
    trunk_name: str
    sip_uri: str
    enabled: bool
    config: dict[str, typing.Any]


class UpdateSipTrunk200Response(pydantic.BaseModel):
    id: str
    description: str
    trunk_name: str
    sip_uri: str
    enabled: bool
    config: dict[str, typing.Any]


class UpdateSipTrunkApplicationJson(pydantic.BaseModel):
    description: str
    room_template: dict[str, typing.Any]
    notification: dict[str, typing.Any]
    trunk_config: dict[str, typing.Any]
    enabled: bool


class ListSipClients200Response(pydantic.BaseModel):
    sip_clients: list[dict[str, typing.Any]]
    total: int
    limit: int
    offset: int


class CreateSipClient200Response(pydantic.BaseModel):
    username: str
    domain: str
    sip_uri: str
    password: str
    expires_at: typing.Optional[str] = None


class CreateSipClientApplicationJson(pydantic.BaseModel):
    username: str
    password: typing.Optional[str] = None
    expires_in_seconds: typing.Optional[int] = None


class GetSipClient200Response(pydantic.BaseModel):
    username: str
    domain: str
    sip_uri: str
    expires_at: typing.Optional[str] = None


class DeleteSipClient200Response(pydantic.BaseModel):
    status: str


class RotateSipClient200Response(pydantic.BaseModel):
    username: str
    domain: str
    sip_uri: str
    password: str
    expires_at: typing.Optional[str] = None


class RotateSipClientApplicationJson(pydantic.BaseModel):
    password: str


class ListRooms200Response(pydantic.BaseModel):
    total_count: int = 0
    data: list[dict[str, typing.Any]]


class CreateRoom200Response(pydantic.BaseModel):
    id: str
    name: str
    api_created: bool = True
    privacy: str
    url: str
    created_at: str
    config: "RoomsRoomNameGetRes"


class CreateRoomApplicationJson(pydantic.BaseModel):
    name: str
    privacy: str
    properties: "RoomProperties"


class SetRoomConfig200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class SetRoomConfigApplicationJson(pydantic.BaseModel):
    privacy: str
    properties: "RoomProperties"


class DeleteRoom200Response(pydantic.BaseModel):
    deleted: bool
    name: str


class SendAppMessage200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class SendAppMessageApplicationJson(pydantic.BaseModel):
    data: dict[str, typing.Any]
    recipient: str = '*'


class GetSessionData200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class SetSessionData200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class SetSessionDataApplicationJson(pydantic.BaseModel):
    data: dict[str, typing.Any]
    merge_strategy: str = pydantic.Field(default='replace', alias="mergeStrategy")
    keys_to_delete: list[str] = pydantic.Field(alias="keysToDelete")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class Eject200Response(pydantic.BaseModel):
    ejected_ids: list[str] = pydantic.Field(alias="ejectedIds")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class EjectApplicationJson(pydantic.BaseModel):
    ids: list[str]
    user_ids: list[str]
    ban: bool = False


class UpdatePermissions200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class UpdatePermissionsApplicationJson(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomRecordingsStart200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomRecordingsUpdate200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomRecordingsStop200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomLivestreamingStart200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomLivestreamingUpdate200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomLivestreamingAddEndpoints200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomLivestreamingRemoveEndpoints200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomLivestreamingStop200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomTranscriptionStart200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomTranscriptionUpdate200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomTranscriptionUpdate404Response(pydantic.BaseModel):
    error: str
    info: str


class RoomTranscriptionUpdateApplicationJson(pydantic.BaseModel):
    instance_id: str = pydantic.Field(alias="instanceId")
    participants: list[str]

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RoomTranscriptionStop200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomTranscriptionStop404Response(pydantic.BaseModel):
    error: str
    info: str


class RoomTranscriptionStopApplicationJson(pydantic.BaseModel):
    instance_id: str = pydantic.Field(alias="instanceId")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RoomDialOutStart200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomDialOutSendDTMF200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomDialOutSendDTMFApplicationJson(pydantic.BaseModel):
    session_id: str = pydantic.Field(alias="sessionId")
    tones: str
    digit_duration_ms: typing.Optional[int] = pydantic.Field(default=None, alias="digitDurationMs")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RoomDialOutStop200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomDialOutStopApplicationJson(pydantic.BaseModel):
    session_id: str = pydantic.Field(alias="sessionId")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RoomSipCallTransfer200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomSipCallTransferApplicationJson(pydantic.BaseModel):
    session_id: str = pydantic.Field(alias="sessionId")
    to_end_point: str = pydantic.Field(alias="toEndPoint")
    caller_id: str = pydantic.Field(alias="callerId")
    wait_before_extension_dial_sec: int = pydantic.Field(default=0, alias="waitBeforeExtensionDialSec")
    extension: str

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RoomSipRefer200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class RoomSipReferApplicationJson(pydantic.BaseModel):
    session_id: str = pydantic.Field(alias="sessionId")
    to_end_point: str = pydantic.Field(alias="toEndPoint")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class CreateMeetingToken200Response(pydantic.BaseModel):
    token: str


class CreateMeetingTokenApplicationJson(pydantic.BaseModel):
    properties: "Properties"


class ValidateMeetingToken200Response(pydantic.BaseModel):
    room_name: str
    is_owner: bool = True
    user_name: str
    start_video_off: bool = True
    start_audio_off: bool = True
    lang: str


class ListRecordings200Response(pydantic.BaseModel):
    total_count: int = 0
    data: list[dict[str, typing.Any]]


class TestOciBucket200Response(pydantic.BaseModel):
    success: bool
    recordings_bucket: typing.Any
    transcription_bucket: typing.Any
    test_file_key: str
    download_link: str
    expires: int


class GetRecordingInfo200Response(pydantic.BaseModel):
    id: str
    room_name: str
    start_ts: int
    status: str
    max_participants: int
    duration: int
    share_token: str
    s3key: str
    mtg_session_id: str = pydantic.Field(alias="mtgSessionId")
    tracks: list[dict[str, typing.Any]]
    storage_provider: str

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DeleteRecording200Response(pydantic.BaseModel):
    deleted: bool
    id: str
    s3_bucket: str
    s3_region: str
    s3_key: str
    storage_provider: str


class GetRecordingLink200Response(pydantic.BaseModel):
    download_link: "SignedRecordingLink"
    expires: int = 0
    storage_provider: str
    validity_capped: bool


class ListTranscript200Response(pydantic.BaseModel):
    total_count: int = 0
    data: list[dict[str, typing.Any]]


class GetTranscriptInfo200Response(pydantic.BaseModel):
    transcript_id: str = pydantic.Field(alias="transcriptId")
    domain_id: str = pydantic.Field(alias="domainId")
    room_id: str = pydantic.Field(alias="roomId")
    mtg_session_id: str = pydantic.Field(alias="mtgSessionId")
    status: str
    is_vtt_available: bool = pydantic.Field(alias="isVttAvailable")
    duration: int
    out_params: dict[str, typing.Any] = pydantic.Field(alias="outParams")
    error: str
    created_at: str
    updated_at: str

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DeleteTranscript200Response(pydantic.BaseModel):
    transcript_id: str = pydantic.Field(alias="transcriptId")
    domain_id: str = pydantic.Field(alias="domainId")
    room_id: str = pydantic.Field(alias="roomId")
    mtg_session_id: str = pydantic.Field(alias="mtgSessionId")
    status: str
    is_vtt_available: bool = pydantic.Field(alias="isVttAvailable")
    duration: int
    out_params: dict[str, typing.Any] = pydantic.Field(alias="outParams")
    created_at: str

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class GetTranscriptLink200Response(pydantic.BaseModel):
    transcript_id: str = pydantic.Field(alias="transcriptId")
    link: "SignedTranscriptLink"
    out_params: dict[str, typing.Any] = pydantic.Field(alias="outParams")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ListDomainDialinConfigs200Response(pydantic.BaseModel):
    total_count: int = 0
    data: list[dict[str, typing.Any]]


class CreateDomainDialConfigInfo400Response(pydantic.BaseModel):
    error: str
    info: str


class DeleteDomainDialinConfig200Response(pydantic.BaseModel):
    status: str


class GetWebhooks200Response(ListResponse[Webhook]):
    pass

class GetWebhookConfig200Response(ListResponse[Webhook]):
    pass

class GetMeetingInfo200Response(pydantic.BaseModel):
    total_count: int
    data: list[dict[str, typing.Any]]


class ListLogs200Response(pydantic.BaseModel):
    logs: list[dict[str, typing.Any]]


class ListLogs400Response(pydantic.BaseModel):
    error: str
    info: str


class ListAPILogs200Response(ListResponse[dict[str, typing.Any]]):
    pass

class ListAPILogs400Response(pydantic.BaseModel):
    error: str
    info: str


class GetPresence200Response(pydantic.BaseModel):
    pass

class BatchRoomCreate200Response(ListResponse[RoomsRoomNameGetRes]):
    pass

class BatchRoomCreateApplicationJson(pydantic.BaseModel):
    rooms: list[dict[str, typing.Any]]


class BatchRoomDelete200Response(pydantic.BaseModel):
    deleted_count: int


class ListAvailableNumbers200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class ListAvailableNumbers400Response(pydantic.BaseModel):
    pass

class ListAvailableNumbers500Response(pydantic.BaseModel):
    pass

class PurchasedPhoneNumbers200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class BuyPhoneNumber200Response(pydantic.BaseModel):
    pass

class BuyPhoneNumber422Response(pydantic.BaseModel):
    errors: list[dict[str, typing.Any]]
    status: int


class BuyPhoneNumberApplicationJson(pydantic.BaseModel):
    number: str


class ReleasePhoneNumber200Response(pydantic.BaseModel):
    status: str


class ReleasePhoneNumber422Response(pydantic.BaseModel):
    error: str


class PinlessCallUpdate200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


class PinlessCallUpdateApplicationJson(pydantic.BaseModel):
    call_id: str = pydantic.Field(alias="callId")
    call_domain: str = pydantic.Field(alias="callDomain")
    sip_uri: str = pydantic.Field(alias="sipUri")

    model_config = pydantic.ConfigDict(populate_by_name=True, serialize_by_alias=True)


class GetDomainConfig200Response(pydantic.BaseModel):
    domain_name: str
    domain_id: str
    config: dict[str, typing.Any]


class SetDomainConfig200Response(pydantic.BaseModel):
    data: dict[str, typing.Any]


def get_subclasses_from_same_file() -> list[typing.Type[pydantic.BaseModel]]:
    """
    Due to how Python declares classes in a module,
    we need to update_forward_refs for all the schemas generated
    here in the situation where there are nested classes.
    """
    calling_frame = inspect.currentframe()
    if not calling_frame:
        return []
    else:
        calling_frame = calling_frame.f_back
    module = inspect.getmodule(calling_frame)

    subclasses = []
    for _, c in inspect.getmembers(module):
        if inspect.isclass(c) and issubclass(c, pydantic.BaseModel) and c != pydantic.BaseModel:
            subclasses.append(c)

    return subclasses


subclasses: list[typing.Type[pydantic.BaseModel]] = get_subclasses_from_same_file()
for c in subclasses:
    c.model_rebuild()