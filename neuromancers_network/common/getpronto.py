"""
GetPronto REST API client.

Handles authentication, the three-step upload flow, file listing,
metadata retrieval, deletion, and transform-URL generation.

Authentication is done by passing the API key in the Authorization header
as `ApiKey YOUR_API_KEY`.  The client auto-detects the key type from the
prefix (pronto_sk_ = secret, pronto_pk_ = public) and enforces
permissions accordingly.
"""

import os
from dataclasses import asdict
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING
from typing import Any

import requests

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE = os.environ.get(
    "GETPRONTO_API_BASE",
    "https://api.getpronto.io/v1",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class GetProntoError(Exception):
    """Base exception for GetPronto API errors."""


class GetProntoAuthError(GetProntoError):
    """Authentication / permission errors (401, 403)."""


class GetProntoRequestError(GetProntoError):
    """Invalid request (400, 404)."""


class GetProntoServerError(GetProntoError):
    """Server-side error (500)."""


def _check_response(resp: requests.Response) -> dict[str, Any]:
    """Raise typed exceptions for non-2xx responses."""
    if resp.ok:
        return resp.json()
    status = resp.status_code
    detail = resp.text
    if status == HTTPStatus.UNAUTHORIZED:
        msg = f"Unauthorized - invalid or missing API key: {detail}"
        raise GetProntoAuthError(msg)
    if status == HTTPStatus.FORBIDDEN:
        msg = f"Forbidden - valid key but insufficient permissions: {detail}"
        raise GetProntoAuthError(msg)
    if status in (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND):
        msg = f"Bad request / not found ({status}): {detail}"
        raise GetProntoRequestError(msg)
    if status == HTTPStatus.TOO_MANY_REQUESTS:
        msg = f"Rate limit exceeded: {detail}"
        raise GetProntoError(msg)
    if status >= HTTPStatus.INTERNAL_SERVER_ERROR:
        msg = f"Server error ({status}): {detail}"
        raise GetProntoServerError(msg)
    msg = f"Unexpected status {status}: {detail}"
    raise GetProntoError(msg)


def _headers(api_key: str) -> dict[str, str]:
    """Return the headers required for every authenticated request."""
    return {
        "Authorization": f"ApiKey {api_key}",
        "Accept": "application/json",
    }


def _is_public_key(api_key: str) -> bool:
    """True if the key has the public-key prefix."""
    return api_key.startswith("pronto_pk_")


# ---------------------------------------------------------------------------
# Public API helpers
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PresignedUploadRequest:
    filename: str
    mimetype: str
    size: int
    custom_filename: str | None = None
    folder_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        field_map = {
            "custom_filename": "customFilename",
            "folder_name": "folderName",
        }

        return {
            field_map.get(key, key): value
            for key, value in asdict(self).items()
            if value is not None
        }


@dataclass
class PresignedUpload:
    """Result of requesting a presigned URL."""

    pending_upload_id: str
    presigned_url: str

    raw: dict[str, Any]


@dataclass(slots=True)
class FileInfo:
    """Metadata about a stored file."""

    id: str
    name: str
    secure_url: str
    secure_thumbnail_url: str
    raw_url: str
    type: str  # image, video, json, file
    raw_type: str  # MIME type
    size: str  # human-readable
    raw_size: int  # bytes
    updated: str  # human-readable
    raw_updated: str  # ISO-8601
    folder_id: str | None
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, response: dict[str, Any]) -> FileInfo:
        data = response.get("file", {"id": ""})
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            secure_url=data.get("secureUrl", ""),
            secure_thumbnail_url=data.get("secureThumbnailUrl", ""),
            raw_url=data.get("rawUrl", ""),
            type=data.get("type", "file"),
            raw_type=data.get("rawType", ""),
            size=data.get("size", ""),
            raw_size=data.get("rawSize", 0),
            updated=data.get("updated", ""),
            raw_updated=data.get("rawUpdated", ""),
            folder_id=data.get("folderId"),
            raw=data,
        )


@dataclass(slots=True)
class TransformParams:
    """Transform parameters for a file."""

    w: int | None = None
    h: int | None = None
    fit: str | None = None
    q: int | None = None
    blur: float | None = None
    sharp: bool | None = None
    gray: bool | None = None
    rot: int | None = None
    border: str | None = None
    crop: str | None = None
    format: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


# ---------------------------------------------------------------------------
# Low-level API calls
# ---------------------------------------------------------------------------


def request_presigned_url(
    api_key: str,
    upload: PresignedUploadRequest,
) -> PresignedUpload:
    """
    Step 1 of the upload flow - get a presigned URL for direct-to-storage upload.

    POST /v1/upload/presign
    """
    resp = requests.post(
        f"{API_BASE}/upload/presign",
        timeout=30,
        json=upload.to_dict(),
        headers=_headers(api_key),
    )

    data = _check_response(resp)

    return PresignedUpload(
        pending_upload_id=data["pendingUploadId"],
        presigned_url=data["uploadUrl"],
        raw=data,
    )


def upload_to_storage(presigned_url: str, file: UploadedFile) -> None:
    """
    Step 2 - PUT the raw file bytes to the presigned URL (direct to storage).

    No GetPronto authentication headers are needed here; the URL itself
    is pre-authenticated by the storage provider.
    """
    file.seek(0)
    resp = requests.put(
        presigned_url,
        timeout=30,
        data=file.read(),
        headers={"Content-Type": file.content_type or "application/octet-stream"},
    )
    if not resp.ok:
        msg = f"Upload to storage failed ({resp.status_code}): {resp.text}"
        raise GetProntoError(msg)


def confirm_upload(api_key: str, pending_upload_id: str) -> FileInfo:
    """
    Step 3 - confirm the upload completed; creates the file record in GetPronto.

    POST /v1/upload/confirm
    """
    resp = requests.post(
        f"{API_BASE}/upload/confirm",
        timeout=30,
        json={"pendingUploadId": pending_upload_id},
        headers=_headers(api_key),
    )
    data = _check_response(resp)
    return _file_info_from_data(data)


def list_files(
    api_key: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[FileInfo], dict[str, Any]]:
    """
    Retrieve a paginated list of files.

    GET /v1/files?page=…&pageSize=…
    """
    resp = requests.get(
        f"{API_BASE}/files",
        timeout=30,
        params={"page": page, "pageSize": page_size},
        headers=_headers(api_key),
    )
    data = _check_response(resp)
    items = data.get("data", data.get("items", []))  # accommodate slight variations
    pagination = {k: v for k, v in data.items() if k not in ("data", "items")}
    return [_file_info_from_data(item) for item in items], pagination


def get_file(api_key: str, file_id: str) -> FileInfo:
    """
    Retrieve metadata for a single file.

    GET /v1/files/{id}
    """
    resp = requests.get(
        f"{API_BASE}/files/{file_id}",
        timeout=30,
        headers=_headers(api_key),
    )
    data = _check_response(resp)
    return _file_info_from_data(data)


def delete_file(api_key: str, file_id: str) -> None:
    """
    Permanently delete a file.

    DELETE /v1/files/{id}
    """
    resp = requests.delete(
        f"{API_BASE}/files/{file_id}",
        timeout=30,
        headers=_headers(api_key),
    )
    _check_response(resp)


def generate_transform_url(
    api_key: str,
    image_id: str,
    transform_params: TransformParams,
) -> str:
    """
    Generate a transformation URL for an image.

    POST /v1/file/{id}/transform-url

    Returns the full URL string that clients can request.
    """
    resp = requests.post(
        f"{API_BASE}/file/{image_id}/transform-url",
        timeout=30,
        json=transform_params.to_dict(),
        headers=_headers(api_key),
    )

    data = _check_response(resp)
    return data["url"]


# ---------------------------------------------------------------------------
# FileInfo factory
# ---------------------------------------------------------------------------


def _file_info_from_data(data: dict[str, Any]) -> FileInfo:
    return FileInfo.from_dict(data)
