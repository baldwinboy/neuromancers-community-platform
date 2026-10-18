"""GetPronto-backed avatar upload for admin-authored profile forms."""

from __future__ import annotations

import logging
import urllib.request

from getpronto.client import files__id_ as delete_getpronto_file
from getpronto.client import upload_confirm
from getpronto.client import upload_presign
from getpronto.schemas import UploadConfirmApplicationJson
from getpronto.schemas import UploadPresignApplicationJson
from neuromancers_network.core.apis import configure_getpronto

logger = logging.getLogger(__name__)

UPLOAD_TIMEOUT_SECONDS = 20


def presign_upload(*, filename, mimetype, size):
    """Request a presigned upload URL and pending id from GetPronto."""
    configure_getpronto()
    return upload_presign(
        data=UploadPresignApplicationJson(
            filename=filename,
            mimetype=mimetype,
            size=size,
        ),
    )


def _put_bytes(upload_url: str, file, mimetype: str) -> None:
    """Upload the file's bytes to the presigned URL."""
    file.seek(0)
    request = urllib.request.Request(  # noqa: S310
        upload_url,
        data=file.read(),
        method="PUT",
        headers={"Content-Type": mimetype},
    )
    with urllib.request.urlopen(  # noqa: S310
        request,
        timeout=UPLOAD_TIMEOUT_SECONDS,
    ) as response:
        response.read()


def _delete_previous(file_id: str) -> None:
    if not file_id:
        return
    try:
        configure_getpronto()
        delete_getpronto_file(id=file_id)
    except Exception:
        logger.exception("Failed to delete previous GetPronto file %s", file_id)


def confirm_upload(*, profile, pending_upload_id: str) -> str:
    """Confirm the upload, replace any previous avatar and return the URL."""
    configure_getpronto()
    result = upload_confirm(
        data=UploadConfirmApplicationJson(pending_upload_id=pending_upload_id),
    )
    file = result.file or {}
    _delete_previous(profile.profile_picture_getpronto_id)
    profile.profile_picture_getpronto_id = file.get("id") or ""
    profile.profile_picture_url = file.get("secureUrl") or file.get("secure_url") or ""
    profile.save(
        update_fields=[
            "profile_picture_getpronto_id",
            "profile_picture_url",
            "updated_at",
        ],
    )
    return profile.profile_picture_url


def store_image(*, page, form, field, file, request=None) -> str:
    """daisIE upload handler: upload *file* to GetPronto and store the profile URL."""
    from neuromancers_network.users.models import UserProfile  # noqa: PLC0415

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        message = "Authentication is required to upload an avatar"
        raise ValueError(message)

    profile, _created = UserProfile.objects.get_or_create(user=user)
    mimetype = getattr(file, "content_type", "") or "application/octet-stream"
    presigned = presign_upload(
        filename=file.name or "avatar",
        mimetype=mimetype,
        size=file.size,
    )
    _put_bytes(presigned.upload_url, file, mimetype)
    return confirm_upload(
        profile=profile,
        pending_upload_id=presigned.pending_upload_id,
    )
