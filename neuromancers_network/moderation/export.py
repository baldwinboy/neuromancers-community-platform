"""Member data export (GDPR access/portability)."""

from __future__ import annotations

import json
import logging

from django.core.files.base import ContentFile
from django.utils import timezone

from neuromancers_network.inbox.events import emit

from .models import DataExportRequest
from .models import ExportStatus

logger = logging.getLogger(__name__)

MEETING_FIELDS = [
    "id",
    "title",
    "status",
    "meeting_type",
    "pricing_type",
    "price",
    "currency",
    "scheduled_at",
    "created_at",
]
REQUEST_FIELDS = ["id", "meeting_id", "status", "price_paid", "created_at"]
BOOKING_FIELDS = [
    "id",
    "meeting_id",
    "status",
    "total_amount",
    "currency",
    "created_at",
]
REVIEW_FIELDS = ["id", "meeting_request_id", "rating", "comment", "created_at"]
NOTIFICATION_FIELDS = ["id", "event_type", "title", "created_at"]


def _rows(queryset, fields):
    return list(queryset.values(*fields))


def collect_user_data(user) -> dict:
    """Return a JSON-safe snapshot of the member's own data."""
    data: dict = {
        "account": {
            "id": user.pk,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "date_of_birth": user.date_of_birth.isoformat()
            if user.date_of_birth
            else None,
            "accepted_tos": user.accepted_tos,
            "is_active": user.is_active,
            "created_at": user.date_joined.isoformat(),
        },
        "meetings": _rows(user.meetings.all(), MEETING_FIELDS),
        "meeting_requests": _rows(user.meeting_requests.all(), REQUEST_FIELDS),
        "bookings": _rows(user.bookings.all(), BOOKING_FIELDS),
        "reviews": _rows(user.reviews_given.all(), REVIEW_FIELDS),
        "notifications": _rows(user.notifications.all(), NOTIFICATION_FIELDS),
    }

    profile = getattr(user, "user_profile", None)
    if profile is not None:
        data["profile"] = {
            "access_needs": profile.access_needs,
            "visibility": profile.visibility,
            "country": profile.country,
            "timezone": profile.timezone,
        }

    peer_profile = getattr(user, "peer_profile", None)
    if peer_profile is not None:
        data["peer_profile"] = {
            "bio": peer_profile.bio,
            "is_approved": peer_profile.is_approved,
            "is_verified": peer_profile.is_verified,
            "default_terms": peer_profile.default_terms,
        }

    return data


def build_export_file(export_request: DataExportRequest) -> DataExportRequest:
    """Render the export to a JSON file and mark the request ready."""
    user = export_request.user
    export_request.status = ExportStatus.PROCESSING
    export_request.save(update_fields=["status", "updated_at"])
    try:
        payload = collect_user_data(user)
        content = json.dumps(payload, indent=2, default=str)
        export_request.file.save(
            f"export-{user.pk}-{export_request.pk}.json",
            ContentFile(content.encode("utf-8")),
            save=False,
        )
        export_request.status = ExportStatus.READY
        export_request.completed_at = timezone.now()
        export_request.error = ""
        export_request.save(
            update_fields=[
                "file",
                "status",
                "completed_at",
                "error",
                "updated_at",
            ],
        )
    except Exception as exc:
        export_request.status = ExportStatus.FAILED
        export_request.error = str(exc)
        export_request.save(update_fields=["status", "error", "updated_at"])
        raise

    try:
        emit(
            "data_export_ready",
            payload={
                "actor_user_id": user.pk,
                "recipient_user_ids": [user.pk],
                "object_type": "dataexport",
                "object_id": export_request.pk,
                "meta": {"export_id": export_request.pk},
            },
            event_ref=f"dataexport.{export_request.pk}.ready",
        )
    except Exception:
        logger.exception("Failed to emit data_export_ready for %s", export_request.pk)
    return export_request


def request_data_export(user) -> DataExportRequest:
    """Queue a data export for *user* and record the request."""
    export = DataExportRequest.objects.create(user=user)
    try:
        from .tasks import build_data_export  # noqa: PLC0415

        build_data_export.delay(export.pk)
    except Exception:
        logger.exception("Failed to enqueue data export %s", export.pk)
    try:
        emit(
            "data_export_requested",
            payload={
                "actor_user_id": user.pk,
                "recipient_user_ids": [user.pk],
                "object_type": "dataexport",
                "object_id": export.pk,
                "meta": {"export_id": export.pk},
            },
            event_ref=f"dataexport.{export.pk}.requested",
        )
    except Exception:
        logger.exception("Failed to emit data_export_requested")
    return export
