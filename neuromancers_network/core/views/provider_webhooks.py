"""Inbound Whereby/Daily webhooks: verify, map to a session, record minutes."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from neuromancers_network.analytics.services import record_activity
from neuromancers_network.analytics.services import record_session
from neuromancers_network.core.models import IntegrationSettings
from neuromancers_network.core.webhook_security import verify_hmac_sha256
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest

logger = logging.getLogger(__name__)


def _timestamp(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except TypeError, ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _minutes(start, end):
    if start is None or end is None or end <= start:
        return None
    return max(0, round((end - start).total_seconds() / 60))


def _daily_payload(payload):
    body = payload.get("payload") or payload
    start = _timestamp(
        body.get("start_ts") or body.get("start_time") or body.get("startTime"),
    )
    end = _timestamp(
        body.get("end_ts") or body.get("end_time") or body.get("endTime"),
    )
    duration = body.get("duration")
    if end is None and start is not None and duration is not None:
        end = start + timedelta(seconds=int(duration))
    return {
        "room_id": body.get("room") or body.get("room_name") or body.get("roomName"),
        "start": start,
        "end": end,
        "event_id": payload.get("id") or body.get("id"),
    }


def _whereby_payload(payload):
    body = payload.get("data") or payload
    return {
        "room_id": (
            body.get("meetingId") or body.get("meeting_id") or body.get("roomName")
        ),
        "start": _timestamp(body.get("startDate") or body.get("start_date")),
        "end": _timestamp(body.get("endDate") or body.get("end_date")),
        "event_id": payload.get("id") or body.get("id"),
    }


def _handle(request, *, provider, secret, header, extractor):
    if not secret:
        logger.error("No %s webhook secret configured", provider)
        return HttpResponseForbidden()

    if not verify_hmac_sha256(
        secret=secret,
        body=request.body,
        signature=request.headers.get(header, ""),
    ):
        logger.warning("Rejected %s webhook with an invalid signature", provider)
        return HttpResponseForbidden()

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest()

    data = extractor(payload)
    return _record_from_payload(provider, request.body, data)


def _record_from_payload(provider, body, data):
    event_id = data["event_id"] or hashlib.sha256(body).hexdigest()
    occurred_at = data["end"] or timezone.now()
    record_activity(
        event_type=f"{provider}_webhook",
        object_type="webhook",
        object_id=event_id,
        occurred_at=occurred_at,
    )

    room_id = data["room_id"]
    minutes = _minutes(data["start"], data["end"])
    if not room_id or minutes is None:
        return JsonResponse({"status": "ignored"})

    request_row = (
        MeetingRequest.objects.filter(
            provider=provider,
            provider_room_id=room_id,
        )
        .select_related("meeting")
        .first()
    )
    if request_row is not None:
        record_session(
            meeting_request=request_row,
            minutes=minutes,
            provider=provider,
            occurred_at=occurred_at,
        )
        return JsonResponse({"status": "ok"})

    meeting = Meeting.objects.filter(
        provider=provider,
        provider_room_id=room_id,
    ).first()
    if meeting is not None:
        record_session(
            meeting=meeting,
            minutes=minutes,
            provider=provider,
            occurred_at=occurred_at,
        )
        return JsonResponse({"status": "ok"})

    logger.info("No session found for %s room %s", provider, room_id)
    return JsonResponse({"status": "ignored"})


@csrf_exempt
@require_POST
def whereby_webhook(request):
    settings_obj = IntegrationSettings.load()
    return _handle(
        request,
        provider="whereby",
        secret=settings_obj.whereby_webhook_secret,
        header="X-Whereby-Signature",
        extractor=_whereby_payload,
    )


@csrf_exempt
@require_POST
def daily_webhook(request):
    settings_obj = IntegrationSettings.load()
    return _handle(
        request,
        provider="daily",
        secret=settings_obj.daily_webhook_secret,
        header="X-Webhook-Signature",
        extractor=_daily_payload,
    )
