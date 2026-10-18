"""Member data export (GDPR access/portability).

Renders a ZIP of CSVs (one per table) using ``.iterator()`` for bounded memory,
stored on the private ``exports`` storage. Exports expire after 48 hours and can
be requested at most once per 24 hours.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import timedelta

from django.core import signing
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from neuromancers_network.inbox.events import emit

from .models import DataExportRequest
from .models import ExportStatus

logger = logging.getLogger(__name__)

EXPORT_TTL_HOURS = 48
EXPORT_COOLDOWN_HOURS = 24
EXPORT_STALE_HOURS = 1
EXPORT_CHUNK_SIZE = 500

ACCOUNT_FIELDS = [
    "id",
    "username",
    "name",
    "email",
    "date_of_birth",
    "accepted_tos",
    "is_active",
    "date_joined",
]
PROFILE_FIELDS = [
    "access_needs",
    "access_needs_visible_to_peer",
    "bio",
    "visibility",
    "country",
    "timezone",
]
PEER_FIELDS = ["bio", "is_approved", "is_verified", "default_terms"]
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

#: ``(filename, related manager, fields)`` for the multi-row CSV tables.
RELATED_TABLES = [
    ("meetings.csv", "meetings", MEETING_FIELDS),
    ("meeting_requests.csv", "meeting_requests", REQUEST_FIELDS),
    ("bookings.csv", "bookings", BOOKING_FIELDS),
    ("reviews.csv", "reviews_given", REVIEW_FIELDS),
    ("notifications.csv", "notifications", NOTIFICATION_FIELDS),
]

_DOWNLOAD_NAMESPACE = "data-export"


def export_download_token(export_request: DataExportRequest) -> str:
    """A short-lived signed token authorising a download of *export_request*."""
    return signing.dumps(export_request.pk, salt=_DOWNLOAD_NAMESPACE, compress=True)


def verify_export_download_token(export_request_pk: int, token: str) -> bool:
    """Whether *token* is a valid, unexpired download token for the export."""
    try:
        payload = signing.loads(
            token,
            salt=_DOWNLOAD_NAMESPACE,
            max_age=EXPORT_TTL_HOURS * 3600,
        )
    except signing.BadSignature:
        return False
    return payload == export_request_pk


def _csv_value(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _csv_bytes(header, rows) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow([_csv_value(row[field]) for field in header])
    return buffer.getvalue().encode("utf-8")


def _table_bytes(queryset, fields) -> bytes:
    rows = queryset.values(*fields).iterator(chunk_size=EXPORT_CHUNK_SIZE)
    return _csv_bytes(fields, rows)


def _account_row(user) -> dict:
    return {field: getattr(user, field, None) for field in ACCOUNT_FIELDS}


def _build_zip(user) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "account.csv",
            _csv_bytes(ACCOUNT_FIELDS, [_account_row(user)]),
        )

        profile = getattr(user, "user_profile", None)
        if profile is not None:
            archive.writestr(
                "profile.csv",
                _csv_bytes(
                    PROFILE_FIELDS,
                    [
                        {
                            field: getattr(profile, field, None)
                            for field in PROFILE_FIELDS
                        },
                    ],
                ),
            )

        peer_profile = getattr(user, "peer_profile", None)
        if peer_profile is not None:
            archive.writestr(
                "peer_profile.csv",
                _csv_bytes(
                    PEER_FIELDS,
                    [
                        {
                            field: getattr(peer_profile, field, None)
                            for field in PEER_FIELDS
                        },
                    ],
                ),
            )

        for filename, manager, fields in RELATED_TABLES:
            archive.writestr(
                filename,
                _table_bytes(getattr(user, manager).all(), fields),
            )
    return buffer.getvalue()


def build_export_file(export_request: DataExportRequest) -> DataExportRequest:
    """Render the export to a ZIP of CSVs and mark the request ready."""
    user = export_request.user
    export_request.status = ExportStatus.PROCESSING
    export_request.save(update_fields=["status", "updated_at"])
    try:
        content = _build_zip(user)
        export_request.file.save(
            f"export-{user.pk}-{export_request.pk}.zip",
            ContentFile(content),
            save=False,
        )
        now = timezone.now()
        export_request.status = ExportStatus.READY
        export_request.completed_at = now
        export_request.expires_at = now + timedelta(hours=EXPORT_TTL_HOURS)
        export_request.error = ""
        export_request.save(
            update_fields=[
                "file",
                "status",
                "completed_at",
                "expires_at",
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
        download_url = reverse(
            "data_export_download",
            args=[export_request.pk, export_download_token(export_request)],
        )
        emit(
            "data_export_ready",
            payload={
                "actor_user_id": user.pk,
                "recipient_user_ids": [user.pk],
                "object_type": "dataexport",
                "object_id": export_request.pk,
                "meta": {"export_id": export_request.pk, "download_url": download_url},
            },
            event_ref=f"dataexport.{export_request.pk}.ready",
        )
    except Exception:
        logger.exception("Failed to emit data_export_ready for %s", export_request.pk)
    return export_request


def request_data_export(user) -> DataExportRequest:
    """Queue a data export for *user* and record the request.

    Raises ``ValueError`` when an export is already in progress or a ready
    export was produced within the cooldown window.
    """
    active = DataExportRequest.objects.filter(
        user=user,
        status__in=[ExportStatus.PENDING, ExportStatus.PROCESSING],
    ).exists()
    if active:
        message = "A data export is already in progress."
        raise ValueError(message)

    cutoff = timezone.now() - timedelta(hours=EXPORT_COOLDOWN_HOURS)
    if DataExportRequest.objects.filter(
        user=user,
        status=ExportStatus.READY,
        completed_at__gte=cutoff,
    ).exists():
        message = "You can request another export later."
        raise ValueError(message)

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


def sweep_data_exports(now=None) -> int:
    """Retry stale jobs and purge expired exports. Returns the purge count."""
    now = now or timezone.now()
    stale_cutoff = now - timedelta(hours=EXPORT_STALE_HOURS)
    stale = DataExportRequest.objects.filter(
        status__in=[ExportStatus.PENDING, ExportStatus.PROCESSING],
        updated_at__lt=stale_cutoff,
    )
    for export in stale:
        try:
            build_export_file(export)
        except Exception:
            logger.exception("Retry failed for data export %s", export.pk)

    purged = 0
    for export in DataExportRequest.objects.filter(
        status=ExportStatus.READY,
        expires_at__lt=now,
    ):
        export.file.delete(save=False)
        export.delete()
        purged += 1
    return purged
