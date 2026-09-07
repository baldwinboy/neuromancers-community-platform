from __future__ import annotations

import typing

from clientele import api as clientele_api

from . import config
from . import schemas

client = clientele_api.APIClient(config=config.Config())


@client.get("/meetings")
def meetings(
    result: schemas.Meetings200Response,
    cursor: str | None = None,
    limit: int | None = None,
    fields: schemas.Fields | None = None,
) -> schemas.Meetings200Response:
    """Get meetings

    Returns a list of meetings.

    """
    return result


@client.post("/meetings")
def meetings(  # noqa: F811
    result: schemas.Meeting,
    data: schemas.MeetingsApplicationJson,
) -> schemas.Meeting:
    """Create meeting

        Creates a transient room that is available between creation and an hour after the given end date. After this time the room will be automatically deleted.
    The URL to this room is present in the response.

    """  # noqa: E501
    return result


@client.get("/meetings/{meeting_id}")
def meetings__meeting_id_(
    result: schemas.Meeting,
    meeting_id: str,
    fields: schemas.Fields | None = None,
) -> schemas.Meeting:
    """Get meeting

    Returns the specified meeting.

    """
    return result


@client.delete("/meetings/{meeting_id}")
def meetings__meeting_id_(result: None, meeting_id: str) -> None:  # noqa: F811
    """Delete meeting

    Deletes the specified meeting. The endpoint is idempotent, meaning it will return the same response even if the meeting has already been deleted.

    """  # noqa: E501
    return result


@client.get("/recordings")
def recordings(
    result: schemas.Recordings200Response,
    room_name: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
) -> schemas.Recordings200Response:
    """Get recordings

    Returns the recordings.

    """
    return result


@client.get("/recordings/{recording_id}")
def recordings__recording_id_(
    result: schemas.Recording,
    recording_id: str,
) -> schemas.Recording:
    """Get recording

    Returns the specified recording metadata.

    """
    return result


@client.delete("/recordings/{recording_id}")
def recordings__recording_id_(result: None, recording_id: str) -> None:  # noqa: F811
    """Delete recording

    Deletes the specified recording. The endpoint is idempotent, meaning it will return the same response even if the recording has already been deleted.

    """  # noqa: E501
    return result


@client.get("/recordings/{recording_id}/access-link")
def recordings__recording_id__access_link(
    result: schemas.RecordingsRecordingIdAccessLink200Response,
    recording_id: str,
    valid_for_seconds: int | None = None,
) -> schemas.RecordingsRecordingIdAccessLink200Response:
    """Get recording access link

    Returns the access link for the specified recording. **Available for Whereby-hosted recordings only**
    """  # noqa: E501
    return result


@client.post("/recordings/bulk-delete")
def recordings_bulk_delete(
    result: None,
    data: schemas.RecordingsBulkDeleteApplicationJson,
) -> None:
    """Bulk delete recordings

       Deletes multiple recordings at once. This is an asynchronous operation. The endpoint returns immediately, and schedules a background job to delete the recordings.
    The endpoint is idempotent, meaning it will return the same response even if the recordings have already been deleted, or the recordings doesn't exist.

    """  # noqa: E501
    return result


@client.get("/transcriptions")
def transcriptions(
    result: schemas.Transcriptions200Response,
    room_name: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
) -> schemas.Transcriptions200Response:
    """Get transcriptions

    Returns a list of transcriptions


    """
    return result


@client.post("/transcriptions")
def transcriptions(  # noqa: F811
    result: schemas.Transcriptions201Response,
    data: schemas.TranscriptionsApplicationJson,
    recording_id: str,
) -> schemas.Transcriptions201Response:
    """Create transcription

    Creates a new transcription for the specified recording.


    """
    return result


@client.get("/transcriptions/{transcription_id}")
def transcriptions__transcription_id_(
    result: schemas.Transcription,
    transcription_id: str,
) -> schemas.Transcription:
    """Get transcription

    Returns the specified transcription metadata.


    """
    return result


@client.delete("/transcriptions/{transcription_id}")
def transcriptions__transcription_id_(result: None, transcription_id: str) -> None:  # noqa: F811
    """Delete transcription

    Deletes the specified transcription. The endpoint is idempotent, meaning it will return the same response even if the transcription has already been deleted.


    """  # noqa: E501
    return result


@client.get("/transcriptions/{transcription_id}/access-link")
def transcriptions__transcription_id__access_link(
    result: schemas.TranscriptionsTranscriptionIdAccessLink200Response,
    transcription_id: str,
    valid_for_seconds: int | None = None,
) -> schemas.TranscriptionsTranscriptionIdAccessLink200Response:
    """Get transcription access link

    Returns a URL that can be used to download the specified transcription. **Available for Whereby-hosted transcriptions only**.


    """  # noqa: E501
    return result


@client.post("/transcriptions/bulk-delete")
def transcriptions_bulk_delete(
    result: None,
    data: schemas.TranscriptionsBulkDeleteApplicationJson,
) -> None:
    """Bulk delete transcriptions

       Deletes multiple transcriptions at once. This is an asynchronous operation. The endpoint returns immediately, and schedules a background job to delete the transcriptions.
    The endpoint is idempotent, meaning it will return the same response even if the transcriptions have already been deleted, or the transcriptions doesn't exist.


    """  # noqa: E501
    return result


@client.get("/summaries")
def summaries(
    result: schemas.Summaries200Response,
    cursor: str | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
) -> schemas.Summaries200Response:
    """Get summaries

       Returns a list of summaries

    Session summaries are currently in Beta and available to selected customers only. Email us at embedded@whereby.com to join our pilot program (terms and conditions apply).
    """  # noqa: E501
    return result


@client.post("/summaries")
def summaries(  # noqa: F811
    result: schemas.Summaries201Response,
    data: schemas.SummariesApplicationJson,
    transcription_id: str,
) -> schemas.Summaries201Response:
    """Create summary

       Creates a new summary for the specified transcription.

    Session summaries are currently in Beta and available to selected customers only. Email us at embedded@whereby.com to join our pilot program (terms and conditions apply).
    """  # noqa: E501
    return result


@client.get("/summaries/{summary_id}")
def summaries__summary_id_(result: schemas.Summary, summary_id: str) -> schemas.Summary:
    """Get summary

       Returns the specified summary.

    Session summaries are currently in Beta and available to selected customers only. Email us at embedded@whereby.com to join our pilot program (terms and conditions apply).
    """  # noqa: E501
    return result


@client.delete("/summaries/{summary_id}")
def summaries__summary_id_(result: None, summary_id: str) -> None:  # noqa: F811
    """Delete summary

       Deletes the specified summary. The endpoint is idempotent, meaning it will return the same response even if the summary has already been deleted.

    Session summaries are currently in Beta and available to selected customers only. Email us at embedded@whereby.com to join our pilot program (terms and conditions apply).
    """  # noqa: E501
    return result


@client.put("/rooms/{room_name}/theme/tokens")
def rooms__room_name__theme_tokens(
    result: None,
    data: schemas.RoomsRoomNameThemeTokensApplicationJson,
    room_name: str,
) -> None:
    """Set room colors

    Set primary, secondary and focus room colors.

    """
    return result


@client.put("/rooms/{room_name}/theme/logo")
def rooms__room_name__theme_logo(
    result: None,
    data: schemas.RoomsRoomNameThemeLogoMultipartFormData
    | schemas.RoomsRoomNameThemeLogoApplicationJson,
    room_name: str,
) -> None:
    """Set room logo

    Upload room logo.

    """
    return result


@client.put("/rooms/{room_name}/theme/room-background")
def rooms__room_name__theme_room_background(
    result: None,
    data: schemas.RoomsRoomNameThemeRoomBackgroundMultipartFormData
    | schemas.RoomsRoomNameThemeRoomBackgroundApplicationJson,
    room_name: str,
) -> None:
    """Set room background

    Use [FormData](https://developer.mozilla.org/en-US/docs/Web/API/FormData/append) to upload a custom background image. JSON objects can be used to set Whereby provided defaults.
    """  # noqa: E501
    return result


@client.put("/rooms/{room_name}/theme/room-knock-page-background")
def rooms__room_name__theme_room_knock_page_background(
    result: None,
    data: schemas.RoomsRoomNameThemeRoomKnockPageBackgroundApplicationJson
    | schemas.RoomsRoomNameThemeRoomKnockPageBackgroundMultipartFormData,
    room_name: str,
) -> None:
    """Set room knock page background

    Use [FormData](https://developer.mozilla.org/en-US/docs/Web/API/FormData/append) to upload a custom knock background image. JSON objects can be used to set Whereby provided defaults.
    """  # noqa: E501
    return result


@client.get("/insights/rooms")
def insights_rooms(  # noqa: PLR0913
    result: schemas.InsightsRooms200Response,
    room_name: dict[str, typing.Any] | None = None,
    created_at: dict[str, typing.Any] | None = None,
    sort_by: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> schemas.InsightsRooms200Response:
    """Get room insights

    Gets a summary of insights collected for rooms.

    """
    return result


@client.get("/insights/room-sessions")
def insights_room_sessions(  # noqa: PLR0913
    result: schemas.InsightsRoomSessions200Response,
    room_name: str,
    room_session_id: str | None = None,
    sort_by: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> schemas.InsightsRoomSessions200Response:
    """Get room session insights

    Gets a summary of usage for each session of a given room.

    """
    return result


@client.get("/insights/participants")
def insights_participants(  # noqa: PLR0913
    result: schemas.InsightsParticipants200Response,
    room_session_id: str,
    external_id: str | None = None,
    sort_by: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> schemas.InsightsParticipants200Response:
    """Get participants

    Gets a list of participants, by either a given session id or external id.

    """
    return result


@client.get("/insights/participant")
def insights_participant(
    result: schemas.InsightsParticipant200Response,
    room_session_id: str,
    participant_id: str,
) -> schemas.InsightsParticipant200Response:
    """Get details for a participant in a session

    Returns session data such as user agent, bandwidth and packet loss for the participant.

    """  # noqa: E501
    return result
