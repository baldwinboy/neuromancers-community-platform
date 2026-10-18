from __future__ import annotations

import typing

from clientele import api as clientele_api
from . import config, schemas

client = clientele_api.APIClient(config=config.Config())



@client.get("/sip-trunk")

def list_sip_trunks(result: schemas.ListSipTrunks200Response, limit: typing.Optional[int] = None, starting_after: typing.Optional[str] = None, ending_before: typing.Optional[str] = None, trunk_name: typing.Optional[str] = None, description: typing.Optional[str] = None, enabled: typing.Optional[bool] = None) -> schemas.ListSipTrunks200Response:
    """/sip-trunk

    List the SIP trunks for your domain (paginated).
    """
    return result


@client.post("/sip-trunk")

def create_sip_trunk(result: schemas.CreateSipTrunk200Response, data: schemas.CreateSipTrunkApplicationJson) -> schemas.CreateSipTrunk200Response:
    """/sip-trunk

    Create a SIP trunk for your domain. Returns the `sip_uri` to point your carrier at, plus the generated `hmac`. `notification.webhook_url` is required and must be LIVE: create sends a signed one-shot `sip_trunk.test` POST that must return 2xx, or the create fails with 400. A trunk must be gated by `allowed_ips`/`credential` or explicitly `is_open: true`.
    """
    return result



@client.get("/sip-trunk/{id}")

def get_sip_trunk(result: schemas.GetSipTrunk200Response, id: str) -> schemas.GetSipTrunk200Response:
    """/sip-trunk/{id}

    Fetch one SIP trunk by id.
    """
    return result


@client.put("/sip-trunk/{id}")

def update_sip_trunk(result: schemas.UpdateSipTrunk200Response, data: schemas.UpdateSipTrunkApplicationJson, id: str) -> schemas.UpdateSipTrunk200Response:
    """/sip-trunk/{id}

    Update a SIP trunk (partial overlay). `trunk_name` is immutable. In `notification`, `hmac: null` ROTATES the secret (Daily regenerates a fresh one); a value sets it; omit to keep the current one. Any update touching `notification` re-sends the signed `sip_trunk.test` probe (with the final hmac) - the endpoint must return 2xx. `trunk_config.credential: null` clears the credential. Admission must remain valid (gated XOR is_open).
    """
    return result



@client.delete("/sip-trunk/{id}")

def delete_sip_trunk(result: None, id: str) -> None:
    """/sip-trunk/{id}

    Delete a SIP trunk (and its Kamailio credential, if any).
    """
    return result



@client.get("/sip-clients")

def list_sip_clients(result: schemas.ListSipClients200Response, limit: typing.Optional[int] = None, offset: typing.Optional[int] = None) -> schemas.ListSipClients200Response:
    """/sip-clients

    List the SIP clients registered for your domain (paginated). Passwords are never returned.
    """
    return result


@client.post("/sip-clients")

def create_sip_client(result: schemas.CreateSipClient200Response, data: schemas.CreateSipClientApplicationJson) -> schemas.CreateSipClient200Response:
    """/sip-clients

    Register a plain SIP client for your domain. Returns the client's SIP URI and a generated `password`, shown ONCE and never returned again. Provide a `username` (a room-style name, optionally suffixed with `.<number>`); supply your own `password` or let one be generated. An optional `expires_in_seconds` sets a TTL after which the client is removed automatically - omit it for a long-lived client. Subject to a per-domain client limit.
    """
    return result



@client.get("/sip-clients/{username}")

def get_sip_client(result: schemas.GetSipClient200Response, username: str) -> schemas.GetSipClient200Response:
    """/sip-clients/{username}

    Fetch one SIP client by username. The password is never returned.
    """
    return result



@client.delete("/sip-clients/{username}")

def delete_sip_client(result: schemas.DeleteSipClient200Response, username: str) -> schemas.DeleteSipClient200Response:
    """/sip-clients/{username}

    Delete a SIP client. After deletion it can no longer register or place calls.
    """
    return result


@client.post("/sip-clients/{username}/rotate")

def rotate_sip_client(result: schemas.RotateSipClient200Response, data: schemas.RotateSipClientApplicationJson, username: str) -> schemas.RotateSipClient200Response:
    """/sip-clients/{username}/rotate

    Rotate a SIP client's password. Supply a new `password` or let one be generated; the new password is returned ONCE. The client's SIP URI and expiry are unchanged.
    """
    return result



@client.get("/rooms")

def list_rooms(result: schemas.ListRooms200Response, limit: typing.Optional[int] = None, ending_before: typing.Optional[str] = None, starting_after: typing.Optional[str] = None) -> schemas.ListRooms200Response:
    """/rooms

    List rooms
    """
    return result


@client.post("/rooms")

def create_room(result: schemas.CreateRoom200Response, data: schemas.CreateRoomApplicationJson) -> schemas.CreateRoom200Response:
    """/rooms

    Create a room
    """
    return result



@client.get("/rooms/{room_name}")

def get_room_config(result: schemas.RoomsRoomNameGetRes, room_name: str) -> schemas.RoomsRoomNameGetRes:
    """rooms/:name

    Get info about a room
    """
    return result


@client.post("/rooms/{room_name}")

def set_room_config(result: schemas.SetRoomConfig200Response, data: schemas.SetRoomConfigApplicationJson, room_name: str) -> schemas.SetRoomConfig200Response:
    """rooms/:name

    Set a room's privacy and config properties
    """
    return result



@client.delete("/rooms/{room_name}")

def delete_room(result: schemas.DeleteRoom200Response, room_name: str) -> schemas.DeleteRoom200Response:
    """rooms/:name

    Delete a room
    """
    return result



@client.get("/rooms/{room_name}/presence")

def get_room_presence(result: schemas.RoomsRoomNamePresenceGetRes, room_name: str, limit: typing.Optional[int] = None, user_id: typing.Annotated[typing.Optional[str], clientele_api.Query(alias="userId")] = None, user_name: typing.Annotated[typing.Optional[str], clientele_api.Query(alias="userName")] = None) -> schemas.RoomsRoomNamePresenceGetRes:
    """rooms/:name/presence

    Get a presence snapshot for a room
    """
    return result


@client.post("/rooms/{room_name}/send-app-message")

def send_app_message(result: schemas.SendAppMessage200Response, data: schemas.SendAppMessageApplicationJson, room_name: str) -> schemas.SendAppMessage200Response:
    """rooms/:name/send-app-message

    Send a message to participants in a room
    """
    return result



@client.get("/rooms/{room_name}/get-session-data")

def get_session_data(result: schemas.GetSessionData200Response, room_name: str) -> schemas.GetSessionData200Response:
    """rooms/:name/get-session-data

    Gets meeting session data
    """
    return result


@client.post("/rooms/{room_name}/set-session-data")

def set_session_data(result: schemas.SetSessionData200Response, data: schemas.SetSessionDataApplicationJson, room_name: str) -> schemas.SetSessionData200Response:
    """rooms/:name/set-session-data

    Sets meeting session data
    """
    return result


@client.post("/rooms/{room_name}/eject")

def eject(result: schemas.Eject200Response, data: schemas.EjectApplicationJson, room_name: str) -> schemas.Eject200Response:
    """rooms/:name/eject

    Ejects participants from a room
    """
    return result


@client.post("/rooms/{room_name}/update-permissions")

def update_permissions(result: schemas.UpdatePermissions200Response, data: schemas.UpdatePermissionsApplicationJson, room_name: str) -> schemas.UpdatePermissions200Response:
    """rooms/:name/update-permissions

    Modifies permissions for one or more participants in a room
    """
    return result


@client.post("/rooms/{room_name}/recordings/start")

def room_recordings_start(result: schemas.RoomRecordingsStart200Response, data: schemas.RecordingStreamingOptions, room_name: str) -> schemas.RoomRecordingsStart200Response:
    """rooms/:name/recordings/start

    Start a recording in a room
    """
    return result


@client.post("/rooms/{room_name}/recordings/update")

def room_recordings_update(result: schemas.RoomRecordingsUpdate200Response, data: schemas.DailyStreamingOptions, room_name: str) -> schemas.RoomRecordingsUpdate200Response:
    """rooms/:name/recordings/update

    Update a recording in a room
    """
    return result


@client.post("/rooms/{room_name}/recordings/stop")

def room_recordings_stop(result: schemas.RoomRecordingsStop200Response, room_name: str) -> schemas.RoomRecordingsStop200Response:
    """rooms/:name/recordings/stop

    Stop a recording in a room
    """
    return result


@client.post("/rooms/{room_name}/live-streaming/start")

def room_livestreaming_start(result: schemas.RoomLivestreamingStart200Response, data: schemas.DailyLiveStreamingOptions, room_name: str) -> schemas.RoomLivestreamingStart200Response:
    """rooms/:name/live-streaming/start

    Start a live stream in a room
    """
    return result


@client.post("/rooms/{room_name}/live-streaming/update")

def room_livestreaming_update(result: schemas.RoomLivestreamingUpdate200Response, data: schemas.DailyLiveStreamingOptions, room_name: str) -> schemas.RoomLivestreamingUpdate200Response:
    """rooms/:name/live-streaming/update

    Update the layout of a live stream that is running in a room.

The update is asynchronous. A `200` means the request was accepted and forwarded to the live stream, not that it has taken effect. The [`streaming.updated`](/reference/rest-api/webhooks/events/streaming-updated) webhook confirms the request was processed; anything the media server rejects or fails to apply later arrives as a [`streaming.warning`](/reference/rest-api/webhooks/events/streaming-warning) webhook, or as a [`live-streaming-warning`](/reference/daily-js/events/error-events#live-streaming-warning) event in daily-js.
    """
    return result


@client.post("/rooms/{room_name}/live-streaming/add-endpoints")

def room_livestreaming_add_endpoints(result: schemas.RoomLivestreamingAddEndpoints200Response, data: schemas.DailyLiveStreamingEndpointsOptions, room_name: str) -> schemas.RoomLivestreamingAddEndpoints200Response:
    """rooms/:name/live-streaming/add-endpoints

    Add RTMP destinations to a live stream that is already running in a room. Each `endpoint` must be the `name` of an `rtmp` entry in the room's [`streaming_endpoints`](/reference/rest-api/rooms/config#streaming_endpoints) property; unknown names are rejected with a `400`. This is the REST counterpart of daily-js [`addLiveStreamingEndpoints()`](/reference/daily-js/instance-methods/add-live-streaming-endpoints).

The update is asynchronous. A `200` means the request was accepted and forwarded to the live stream, not that it has taken effect. The [`streaming.updated`](/reference/rest-api/webhooks/events/streaming-updated) webhook confirms the request was processed; anything the media server rejects or fails to apply later arrives as a [`streaming.warning`](/reference/rest-api/webhooks/events/streaming-warning) webhook, or as a [`live-streaming-warning`](/reference/daily-js/events/error-events#live-streaming-warning) event in daily-js.
    """
    return result


@client.post("/rooms/{room_name}/live-streaming/remove-endpoints")

def room_livestreaming_remove_endpoints(result: schemas.RoomLivestreamingRemoveEndpoints200Response, data: schemas.DailyLiveStreamingEndpointsOptions, room_name: str) -> schemas.RoomLivestreamingRemoveEndpoints200Response:
    """rooms/:name/live-streaming/remove-endpoints

    Remove RTMP destinations from a live stream that is running in a room. Each `endpoint` must be the `name` of an `rtmp` entry in the room's [`streaming_endpoints`](/reference/rest-api/rooms/config#streaming_endpoints) property; unknown names are rejected with a `400`. This is the REST counterpart of daily-js [`removeLiveStreamingEndpoints()`](/reference/daily-js/instance-methods/remove-live-streaming-endpoints). A stream cannot be left with no destination: a request that would remove every endpoint is rejected by the media server and reported as a `streaming.warning`; stop the live stream instead.

The update is asynchronous. A `200` means the request was accepted and forwarded to the live stream, not that it has taken effect. The [`streaming.updated`](/reference/rest-api/webhooks/events/streaming-updated) webhook confirms the request was processed; anything the media server rejects or fails to apply later arrives as a [`streaming.warning`](/reference/rest-api/webhooks/events/streaming-warning) webhook, or as a [`live-streaming-warning`](/reference/daily-js/events/error-events#live-streaming-warning) event in daily-js.
    """
    return result


@client.post("/rooms/{room_name}/live-streaming/stop")

def room_livestreaming_stop(result: schemas.RoomLivestreamingStop200Response, room_name: str) -> schemas.RoomLivestreamingStop200Response:
    """rooms/:name/live-streaming/stop

    Stop a live stream in a room
    """
    return result


@client.post("/rooms/{room_name}/transcription/start")

def room_transcription_start(result: schemas.RoomTranscriptionStart200Response, data: schemas.TranscriptionProperties, room_name: str) -> schemas.RoomTranscriptionStart200Response:
    """rooms/:name/transcription/start

    Start a transcription in a room
    """
    return result


@client.post("/rooms/{room_name}/transcription/update", response_map={200: schemas.RoomTranscriptionUpdate200Response, 404: schemas.RoomTranscriptionUpdate404Response})

def room_transcription_update(result: schemas.RoomTranscriptionUpdate200Response | schemas.RoomTranscriptionUpdate404Response, data: schemas.RoomTranscriptionUpdateApplicationJson, room_name: str) -> schemas.RoomTranscriptionUpdate200Response | schemas.RoomTranscriptionUpdate404Response:
    """rooms/:name/transcription/update

    Update the set of participants being transcribed
    """
    return result


@client.post("/rooms/{room_name}/transcription/stop", response_map={200: schemas.RoomTranscriptionStop200Response, 404: schemas.RoomTranscriptionStop404Response})

def room_transcription_stop(result: schemas.RoomTranscriptionStop200Response | schemas.RoomTranscriptionStop404Response, data: schemas.RoomTranscriptionStopApplicationJson, room_name: str) -> schemas.RoomTranscriptionStop200Response | schemas.RoomTranscriptionStop404Response:
    """rooms/:name/transcription/stop

    Stop a transcription in a room
    """
    return result


@client.post("/rooms/{room_name}/dialOut/start")

def room_dial_out_start(result: schemas.RoomDialOutStart200Response, data: schemas.DialoutProperties, room_name: str) -> schemas.RoomDialOutStart200Response:
    """rooms/:name/dialOut/start

    Start a dial-out in a room
    """
    return result


@client.post("/rooms/{room_name}/dialOut/sendDTMF")

def room_dial_out_send_d_t_m_f(result: schemas.RoomDialOutSendDTMF200Response, data: schemas.RoomDialOutSendDTMFApplicationJson, room_name: str) -> schemas.RoomDialOutSendDTMF200Response:
    """rooms/:name/dialOut/sendDTMF

    send DTMF digits on the dial-out
    """
    return result


@client.post("/rooms/{room_name}/dialOut/stop")

def room_dial_out_stop(result: schemas.RoomDialOutStop200Response, data: schemas.RoomDialOutStopApplicationJson, room_name: str) -> schemas.RoomDialOutStop200Response:
    """rooms/:name/dialOut/stop

    Stop a dial out in a room
    """
    return result


@client.post("/rooms/{room_name}/sipCallTransfer")

def room_sip_call_transfer(result: schemas.RoomSipCallTransfer200Response, data: schemas.RoomSipCallTransferApplicationJson, room_name: str) -> schemas.RoomSipCallTransfer200Response:
    """rooms/:name/sipCallTransfer

    transfer sip/pstn call
    """
    return result


@client.post("/rooms/{room_name}/sipRefer")

def room_sip_refer(result: schemas.RoomSipRefer200Response, data: schemas.RoomSipReferApplicationJson, room_name: str) -> schemas.RoomSipRefer200Response:
    """rooms/:name/sipRefer

    refer a sip call to other sip endpoint
    """
    return result


@client.post("/meeting-tokens")

def create_meeting_token(result: schemas.CreateMeetingToken200Response, data: schemas.CreateMeetingTokenApplicationJson) -> schemas.CreateMeetingToken200Response:
    """meeting-tokens

    Create a meeting token
    """
    return result



@client.get("/meeting-tokens/{meeting_token}")

def validate_meeting_token(result: schemas.ValidateMeetingToken200Response, meeting_token: str, ignore_nbf: typing.Annotated[typing.Optional[bool], clientele_api.Query(alias="ignoreNbf")] = None) -> schemas.ValidateMeetingToken200Response:
    """meeting-tokens/:meeting_token

    Validate meeting tokens
    """
    return result



@client.get("/recordings")

def list_recordings(result: schemas.ListRecordings200Response, limit: typing.Optional[int] = None, ending_before: typing.Optional[str] = None, starting_after: typing.Optional[str] = None, room_name: typing.Optional[str] = None) -> schemas.ListRecordings200Response:
    """/recordings

    List recordings
    """
    return result



@client.get("/recordings/test-oci-bucket")

def test_oci_bucket(result: schemas.TestOciBucket200Response, property: typing.Optional[str] = None, room_name: typing.Annotated[typing.Optional[str], clientele_api.Query(alias="roomName")] = None) -> schemas.TestOciBucket200Response:
    """/recordings/test-oci-bucket

    Verify that an OCI bucket configuration works, by uploading a small test file (`daily-co-test-upload.txt`) to it through the OCI S3 compatibility API.

Unlike S3 buckets, an OCI bucket configuration is **not** checked when you set it — the `Admit` policy may not have propagated yet (see the [custom OCI storage guide](/docs/guides/features/recording/custom-oci-storage)). Setting the property therefore succeeds even when the bucket is not usable, and this endpoint is how you confirm the setup before relying on it.

Only OCI buckets can be tested. Calling this against a bucket whose `storage_provider` is `aws` returns a `400`.

On success the response echoes the tested configuration under a key matching the `property` query parameter — `recordings_bucket` by default, or `transcription_bucket`. A `download_link` and `expires` are returned only when the configuration has `allow_api_access` set to `true`; the link is valid for one hour. Storage credentials are never included in the response.
    """
    return result



@client.get("/recordings/{recording_id}")

def get_recording_info(result: schemas.GetRecordingInfo200Response, recording_id: str) -> schemas.GetRecordingInfo200Response:
    """recordings/:id

    Get info about a recording
    """
    return result



@client.delete("/recordings/{recording_id}")

def delete_recording(result: schemas.DeleteRecording200Response, recording_id: str) -> schemas.DeleteRecording200Response:
    """recordings/:id

    Delete a recording
    """
    return result



@client.get("/recordings/{recording_id}/access-link")

def get_recording_link(result: schemas.GetRecordingLink200Response, recording_id: str, valid_for_secs: typing.Optional[int] = None) -> schemas.GetRecordingLink200Response:
    """recordings/:id/access-link

    Generate an access link for a recording. The `download_link` is a short-lived signed URL: see the [access links guide](/docs/rest-api/access-links) for more information.
    """
    return result



@client.get("/transcript")

def list_transcript(result: schemas.ListTranscript200Response, limit: typing.Optional[int] = None, ending_before: typing.Optional[str] = None, starting_after: typing.Optional[str] = None, room_id: typing.Annotated[typing.Optional[str], clientele_api.Query(alias="roomId")] = None, room_name: typing.Optional[str] = None, mtg_session_id: typing.Annotated[typing.Optional[str], clientele_api.Query(alias="mtgSessionId")] = None) -> schemas.ListTranscript200Response:
    """/transcript

    List transcripts
    """
    return result



@client.get("/transcript/{transcript_id}")

def get_transcript_info(result: schemas.GetTranscriptInfo200Response, transcript_id: str) -> schemas.GetTranscriptInfo200Response:
    """transcript/:transcriptId

    Get info about a Transcript
    """
    return result



@client.delete("/transcript/{transcript_id}")

def delete_transcript(result: schemas.DeleteTranscript200Response, transcript_id: str) -> schemas.DeleteTranscript200Response:
    """transcript/:id

    Delete a transcript
    """
    return result



@client.get("/transcript/{transcript_id}/access-link")

def get_transcript_link(result: schemas.GetTranscriptLink200Response, transcript_id: str) -> schemas.GetTranscriptLink200Response:
    """transcript/:id/access-link

    Generate an access link for a transcript. The `link` is a short-lived signed URL: see the [access links guide](/docs/rest-api/access-links) for more information.
    """
    return result



@client.get("/domain-dialin-config")

def list_domain_dialin_configs(result: schemas.ListDomainDialinConfigs200Response, limit: typing.Optional[int] = None, ending_before: typing.Optional[str] = None, starting_after: typing.Optional[str] = None, phone_number: typing.Optional[str] = None, phone_numbers: typing.Optional[str] = None, sip_username: typing.Optional[str] = None, name_prefix: typing.Optional[str] = None, type_: typing.Annotated[typing.Optional[str], clientele_api.Query(alias="type")] = None) -> schemas.ListDomainDialinConfigs200Response:
    """/domain-dialin-config

    List all the pinless_dialin and pin_dialin configs for the domain, with pagination
    """
    return result


@client.post("/domain-dialin-config", response_map={200: schemas.DomainDialinConfigInfoRes, 400: schemas.CreateDomainDialConfigInfo400Response})

def create_domain_dial_config_info(result: schemas.CreateDomainDialConfigInfo400Response | schemas.DomainDialinConfigInfoRes, data: schemas.DomainDialinConfigCreateReq) -> schemas.CreateDomainDialConfigInfo400Response | schemas.DomainDialinConfigInfoRes:
    """create new config

    create a new pinless_dialin or pin_dialin config
    """
    return result



@client.get("/domain-dialin-config/{id}")

def get_domain_dialin_config_info(result: schemas.DomainDialinConfigInfoRes, id: str) -> schemas.DomainDialinConfigInfoRes:
    """domain-dialin-config/:id

    Get info about an existing pinless_dialin or pin_dialin config
    """
    return result


@client.put("/domain-dialin-config/{id}")

def update_domain_dial_config_info(result: schemas.DomainDialinConfigInfoRes, data: schemas.DomainDialinConfigUpdateReq, id: str) -> schemas.DomainDialinConfigInfoRes:
    """domain-dialin-config/:id

    update an existing pinless_dialin or pin_dialin config
    """
    return result



@client.delete("/domain-dialin-config/{id}")

def delete_domain_dialin_config(result: schemas.DeleteDomainDialinConfig200Response, id: str) -> schemas.DeleteDomainDialinConfig200Response:
    """domain-dialin-config/:id

    Delete a given pinless_dialin or pin_dialin config
    """
    return result



@client.get("/webhooks")

def get_webhooks(result: schemas.GetWebhooks200Response) -> schemas.GetWebhooks200Response:
    """/webhooks

    Get Webhooks
    """
    return result


@client.post("/webhooks")

def create_webhook(result: schemas.Webhook, data: schemas.PostWebhook) -> schemas.Webhook:
    """/webhooks

    Create a webhook
    """
    return result



@client.get("/webhooks/{id}")

def get_webhook_config(result: schemas.GetWebhookConfig200Response, id: str) -> schemas.GetWebhookConfig200Response:
    """webhooks/:id

    Get info about a webhook
    """
    return result


@client.post("/webhooks/{id}")

def update_webhook_config(result: schemas.Webhook, data: schemas.UpdateWebhook, id: str) -> schemas.Webhook:
    """webhooks/:id

    Update webhook config
    """
    return result



@client.delete("/webhooks/{id}")

def delete_webhook(result: None, id: str) -> None:
    """webhooks/:id

    Delete a webhook
    """
    return result



@client.get("/meetings")

def get_meeting_info(result: schemas.GetMeetingInfo200Response, room: typing.Optional[list[str]] = None, timeframe_start: typing.Optional[int] = None, timeframe_end: typing.Optional[int] = None, limit: typing.Optional[int] = None, starting_after: typing.Optional[str] = None, ending_before: typing.Optional[str] = None, ongoing: typing.Optional[bool] = None, no_participants: typing.Optional[bool] = None) -> schemas.GetMeetingInfo200Response:
    """/meetings

    retrieve meeting analytics
    """
    return result



@client.get("/meetings/{meeting}")

def get_individual_meeting_info(result: schemas.MeetingsMeetingGetRes, meeting: str) -> schemas.MeetingsMeetingGetRes:
    """/meetings/:meeting

    retrieve info about a particular meeting
    """
    return result



@client.get("/meetings/{meeting}/participants")

def get_meeting_participants(result: schemas.MeetingParticipantsGetRes, meeting: str, limit: typing.Optional[int] = None, joined_after: typing.Optional[str] = None, joined_before: typing.Optional[str] = None) -> schemas.MeetingParticipantsGetRes:
    """/meetings/:meeting/participants

    retrieve info about the participants in a particular meeting
    """
    return result



@client.get("/logs", response_map={200: schemas.ListLogs200Response, 400: schemas.ListLogs400Response})

def list_logs(result: schemas.ListLogs200Response | schemas.ListLogs400Response, include_logs: typing.Annotated[typing.Optional[bool], clientele_api.Query(alias="includeLogs")] = None, include_metrics: typing.Annotated[typing.Optional[bool], clientele_api.Query(alias="includeMetrics")] = None, user_session_id: typing.Annotated[typing.Optional[str], clientele_api.Query(alias="userSessionId")] = None, mtg_session_id: typing.Annotated[typing.Optional[str], clientele_api.Query(alias="mtgSessionId")] = None, log_level: typing.Annotated[typing.Optional[str], clientele_api.Query(alias="logLevel")] = None, order: typing.Optional[str] = None, start_time: typing.Annotated[typing.Optional[int], clientele_api.Query(alias="startTime")] = None, end_time: typing.Annotated[typing.Optional[int], clientele_api.Query(alias="endTime")] = None, limit: typing.Optional[int] = None, offset: typing.Optional[int] = None) -> schemas.ListLogs200Response | schemas.ListLogs400Response:
    """/logs
    """
    return result



@client.get("/logs/api", response_map={200: schemas.ListAPILogs200Response, 400: schemas.ListAPILogs400Response})

def list_a_p_i_logs(result: schemas.ListAPILogs200Response | schemas.ListAPILogs400Response, starting_after: typing.Optional[str] = None, ending_before: typing.Optional[str] = None, limit: typing.Optional[int] = None, source: typing.Optional[str] = None, url: typing.Optional[str] = None) -> schemas.ListAPILogs200Response | schemas.ListAPILogs400Response:
    """/logs/api
    """
    return result



@client.get("/presence")

def get_presence(result: schemas.GetPresence200Response) -> schemas.GetPresence200Response:
    """/presence
    """
    return result


@client.post("/batch/rooms")

def batch_room_create(result: schemas.BatchRoomCreate200Response, data: schemas.BatchRoomCreateApplicationJson) -> schemas.BatchRoomCreate200Response:
    """/batch/rooms

    Create rooms in bulk
    """
    return result



@client.delete("/batch/rooms")

def batch_room_delete(result: schemas.BatchRoomDelete200Response) -> schemas.BatchRoomDelete200Response:
    """/batch/rooms

    Delete rooms in bulk
    """
    return result



@client.get("/list-available-numbers", response_map={200: schemas.ListAvailableNumbers200Response, 400: schemas.ListAvailableNumbers400Response, 500: schemas.ListAvailableNumbers500Response})

def list_available_numbers(result: schemas.ListAvailableNumbers200Response | schemas.ListAvailableNumbers400Response | schemas.ListAvailableNumbers500Response, areacode: typing.Optional[str] = None, region: typing.Optional[str] = None, city: typing.Optional[str] = None, contains: typing.Optional[str] = None, starts_with: typing.Optional[str] = None, ends_with: typing.Optional[str] = None) -> schemas.ListAvailableNumbers200Response | schemas.ListAvailableNumbers400Response | schemas.ListAvailableNumbers500Response:
    """/list-available-numbers

    Search for available phone numbers to purchase
    """
    return result



@client.get("/purchased-phone-numbers")

def purchased_phone_numbers(result: schemas.PurchasedPhoneNumbers200Response, limit: typing.Optional[int] = None, ending_before: typing.Optional[str] = None, starting_after: typing.Optional[str] = None, filter_name: typing.Optional[str] = None, filter_number: typing.Optional[str] = None) -> schemas.PurchasedPhoneNumbers200Response:
    """/purchased-phone-numbers

    List the purchased phone numbers for this domain
    """
    return result


@client.post("/buy-phone-number", response_map={200: schemas.BuyPhoneNumber200Response, 422: schemas.BuyPhoneNumber422Response})

def buy_phone_number(result: schemas.BuyPhoneNumber200Response | schemas.BuyPhoneNumber422Response, data: schemas.BuyPhoneNumberApplicationJson) -> schemas.BuyPhoneNumber200Response | schemas.BuyPhoneNumber422Response:
    """/buy-phone-number

    This will buy a phone number. In the POST request you can either provide the phone number you want to buy, or leave it empty. If the specified `number` is still available, it will be bought or the API will return a failure. Alternatively, if you skipped the `number` field, a random phone number from California (CA) will be bought.
    """
    return result



@client.delete("/release-phone-number/{id}", response_map={200: schemas.ReleasePhoneNumber200Response, 422: schemas.ReleasePhoneNumber422Response})

def release_phone_number(result: schemas.ReleasePhoneNumber200Response | schemas.ReleasePhoneNumber422Response, id: str) -> schemas.ReleasePhoneNumber200Response | schemas.ReleasePhoneNumber422Response:
    """release-phone-number/:id

    Release a purchased number. The number is referenced by its id. A number cannot be deleted within the 14 days of purchase. Calling this API before this period expires results in an error.
    """
    return result


@client.post("/dialin/pinlessCallUpdate")

def pinless_call_update(result: schemas.PinlessCallUpdate200Response, data: schemas.PinlessCallUpdateApplicationJson) -> schemas.PinlessCallUpdate200Response:
    """/dialin/pinlessCallUpdate

    Direct a SIP or PSTN call on hold to a specified SIP URI associated to a Daily Room.
    """
    return result



@client.get("/")

def get_domain_config(result: schemas.GetDomainConfig200Response) -> schemas.GetDomainConfig200Response:
    """Get domain configuration

    Get top-level configuration of your domain
    """
    return result


@client.post("/")

def set_domain_config(result: schemas.SetDomainConfig200Response, data: schemas.Domain) -> schemas.SetDomainConfig200Response:
    """Set domain configuration

    Set top-level configuration options for your domain
    """
    return result