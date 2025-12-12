import random
from datetime import datetime

import requests
from django.conf import settings
from django.utils.translation import gettext as _

from apps.accounts.models_users.user import User
from apps.events.models_pages.wagtail_settings import WherebySettings


def subtract_event(a: tuple[datetime, datetime], b: tuple[datetime, datetime]):
    """
    Gte non-overlapping times
    """
    results = []
    (a_start, a_end) = a
    (b_start, b_end) = b

    # No overlap at all
    if a_end <= b_start or a_start >= b_end:
        results.append((a_start, a_end))

    # y fully inside x
    elif b_start > a_start and b_end < a_end:
        results.append((a_start, b_start))
        results.append((b_end, a_end))

    # y overlaps start of x
    elif b_start <= a_start and b_end < a_end and b_end > a_start:
        results.append((b_end, a_end))

    # y overlaps end of x
    elif b_start > a_start and b_start < a_end and b_end >= a_end:
        results.append((a_start, b_start))

    # y fully covers x
    # (no need to add anything if y covers x completely)

    return results


def get_languages() -> dict[str, str]:
    return {k: _(v) for k, v in settings.LANGUAGES}


def get_language_display(iso: str) -> str | None:
    all_languages = get_languages()
    return all_languages.get(iso)


def stable_price():
    return random.choice([0, 500, 1000, 1500])  # repeatable small set


def stable_langs():
    return random.choice(["en", "en,fr", "en,es"])


def stable_durations():
    return random.choice(["30,60", "20,40,60"])


def get_host_user():
    return User.objects.filter(groups__name="Peer").order_by("?").first()


def get_whereby_api_key(request=None):
    """
    Get Whereby API key from Wagtail settings.

    Args:
        request: Django request object (used to load Wagtail settings)

    Returns:
        str: API key or None
    """
    try:
        settings = WherebySettings.load(request)
        return settings.api_key or settings.WHEREBY_API_KEY
    except Exception:
        return settings.WHEREBY_API_KEY


def create_whereby_meeting(
    start_time, end_time, room_name_prefix="NEUROMANCERS", request=None
):
    """
    Create a Whereby meeting room using the Whereby API.

    Args:
        start_time: datetime when the meeting should start
        end_time: datetime when the meeting should end
        room_name_prefix: Optional prefix for the room name
        request: Django request object (used to load API key from Wagtail settings)

    Returns:
        dict with 'roomUrl' and 'hostRoomUrl' if successful, None if failed
    """
    api_key = get_whereby_api_key(request)

    if not api_key:
        return None

    # Convert to ISO format for API
    start_date = start_time.isoformat()
    end_date = end_time.isoformat()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "startDate": start_date,
        "endDate": end_date,
        "fields": ["hostRoomUrl"],  # Get host URL for additional controls
        "roomNamePrefix": room_name_prefix,
        "roomMode": "normal",  # or "group" for group sessions
    }

    try:
        response = requests.post(
            "https://api.whereby.dev/v1/meetings",
            json=data,
            headers=headers,
            timeout=10,
        )

        if response.status_code == 201:
            result = response.json()
            return {
                "roomUrl": result.get("roomUrl"),
                "hostRoomUrl": result.get("hostRoomUrl"),
                "meetingId": result.get("meetingId"),
            }
        else:
            # Log error for debugging
            print(f"Whereby API error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Whereby API request failed: {str(e)}")
        return None


def generate_peer_meeting_link_if_needed(session_request):
    """
    Generate a Whereby meeting link for a session request if:
    1. No meeting link exists
    2. Session is published
    3. Session starts within 1 hour
    4. Request is approved

    Args:
        session_request: PeerSessionRequest instance

    Returns:
        str: Meeting link URL or None
    """
    from datetime import timedelta

    from django.utils import timezone

    # Only generate for approved requests
    from apps.events.choices import SessionRequestStatusChoices

    if (
        session_request.status != SessionRequestStatusChoices.APPROVED
        or not session_request.session.is_published
    ):
        return None

    # Check if already has a link
    if session_request.meeting_link:
        return session_request.meeting_link

    # Check if within 1 hour of start time
    now = timezone.now()
    time_until_session = session_request.starts_at - now

    if timedelta(0) <= time_until_session <= timedelta(hours=1):
        # Generate meeting
        result = create_whereby_meeting(
            session_request.starts_at,
            session_request.ends_at,
            room_name_prefix=f"NEUROMANCERS-{session_request.session.host.username}",
        )

        if result and result.get("roomUrl"):
            session_request.meeting_link = result["roomUrl"]
            session_request.save(update_fields=["meeting_link"])
            return result["roomUrl"]

    return None


def generate_group_meeting_link_if_needed(session):
    """
    Generate a Whereby meeting link for a session if:
    1. No meeting link exists
    2. Session is published
    3. Session starts within 1 hour

    Args:
        session: GroupSession instance

    Returns:
        str: Meeting link URL or None
    """
    from datetime import timedelta

    from django.utils import timezone

    # Only generate for approved requests
    from apps.events.choices import SessionRequestStatusChoices

    if session.status != SessionRequestStatusChoices.APPROVED:
        return None

    # Check if already has a link
    if session.meeting_link:
        return session.meeting_link

    # Check if within 1 hour of start time
    now = timezone.now()
    time_until_session = session.starts_at - now

    if timedelta(0) <= time_until_session <= timedelta(hours=1):
        # Generate meeting
        result = create_whereby_meeting(
            session.starts_at,
            session.ends_at,
            room_name_prefix=f"NEUROMANCERS-{session.host.username}",
        )

        if result and result.get("roomUrl"):
            session.meeting_link = result["roomUrl"]
            session.save(update_fields=["meeting_link"])
            return result["roomUrl"]

    return None
