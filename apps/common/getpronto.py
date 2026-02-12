"""
GetPronto mini-SDK

A lightweight Python client for the GetPronto REST API.
Mirrors the project's Stripe SDK pattern in apps/common/utils.py:
every public function accepts an optional ``request`` so that
Wagtail Admin overrides (ImageUploadSettings) take precedence
over values in django.conf.settings.

API reference: https://www.getpronto.io/docs/api-reference/overview
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import IO, Any

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from PIL import Image
from wagtail.contrib.settings.registry import registry

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.getpronto.io/v1"
DEFAULT_QUALITY = 85  # JPEG/WebP quality for compression
MAX_IMAGE_DIMENSION = 5000
TOKEN_CACHE_KEY = "getpronto_api_token"
TOKEN_CACHE_TIMEOUT = 60 * 60  # 1 hour


def _load_image_upload_settings(request: HttpRequest):
    """
    Load ImageUploadSettings from the Wagtail registry.
    """
    return registry.get_by_natural_key("events", "ImageUploadSettings").load(
        request_or_site=request
    )


def get_api_key(request: HttpRequest | None = None) -> str:
    """
    Return the GetPronto API key.
    Checks Wagtail Admin ``ImageUploadSettings`` first when *request*
    is provided, then falls back to ``settings.GETPRONTO_API_KEY``.
    """
    if not request:
        return settings.GETPRONTO_API_KEY

    ws = _load_image_upload_settings(request)
    return ws.get_pronto_api_key or settings.GETPRONTO_API_KEY


def get_api_url(request: HttpRequest | None = None) -> str:
    """
    Return the GetPronto base API URL (without trailing slash).
    Checks Wagtail Admin ``ImageUploadSettings`` first when *request*
    is provided, then falls back to ``settings.GETPRONTO_API_URL``.
    """
    if not request:
        base = getattr(settings, "GETPRONTO_API_URL", DEFAULT_BASE_URL)
        return base.rstrip("/")

    ws = _load_image_upload_settings(request)
    base = ws.get_pronto_api_url or getattr(
        settings, "GETPRONTO_API_URL", DEFAULT_BASE_URL
    )
    return base.rstrip("/")


def get_api_email(request: HttpRequest | None = None) -> str:
    """
    Return the GetPronto API email.
    Checks Wagtail Admin ``ImageUploadSettings`` first when *request* is provided,
    then falls back to ``settings.GETPRONTO_EMAIL``.
    """
    if not requests.request:
        return settings.GETPRONTO_EMAIL
    ws = _load_image_upload_settings(request)
    return ws.get_pronto_email or settings.GETPRONTO_EMAIL


def get_api_password(request: HttpRequest | None = None) -> str:
    """
    Return the GetPronto API password.
    Checks Wagtail Admin ``ImageUploadSettings`` first when *request* is provided,
    then falls back to ``settings.GETPRONTO_PASSWORD``.
    """
    if not requests.request:
        return settings.GETPRONTO_PASSWORD
    ws = _load_image_upload_settings(request)
    return ws.get_pronto_password or settings.GETPRONTO_PASSWORD


@dataclass
class ProntoFile:
    """
    Represents a file object returned by the GetPronto API.
    """

    id: str
    filename: str
    mimetype: str
    size: int
    created_at: str
    url: str

    @classmethod
    def from_api(cls, data: dict) -> "ProntoFile":
        return cls(
            id=data["id"],
            filename=data["filename"],
            mimetype=data["mimetype"],
            size=data["size"],
            created_at=data["createdAt"],
            url=data["url"],
        )


@dataclass
class ProntoPagination:
    """Pagination metadata from list endpoints."""

    page: int
    page_size: int
    total_count: int
    total_pages: int

    @classmethod
    def from_api(cls, data: dict) -> "ProntoPagination":
        return cls(
            page=data["page"],
            page_size=data["pageSize"],
            total_count=data["totalCount"],
            total_pages=data["totalPages"],
        )


@dataclass
class ProntoFileList:
    """Paginated list of files."""

    files: list[ProntoFile] = field(default_factory=list)
    pagination: ProntoPagination | None = None


@dataclass
class TransformResult:
    """Result from the transform-url endpoint."""

    url: str
    original_file: ProntoFile | None = None
    transformations: dict = field(default_factory=dict)


class GetProntoError(Exception):
    """Base exception for GetPronto API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class GetProntoAuthError(GetProntoError):
    """Raised for 401/403 responses."""


class GetProntoNotFoundError(GetProntoError):
    """Raised for 404 responses."""


class GetProntoRateLimitError(GetProntoError):
    """Raised for 429 responses."""


class GetProntoClient:
    """Lightweight REST client for the GetPronto API.

    Usage::

        from apps.common.getpronto import GetProntoClient

        client = GetProntoClient(request=request)  # uses Wagtail settings
        result = client.upload_file(file_obj, filename="avatar.webp")
        print(result.url)
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_url: str | None = None,
        request: HttpRequest | None = None,
        timeout: int = 30,
    ):
        self._api_key = api_key or get_api_key(request)
        self._api_url = api_url or get_api_url(request)
        self._timeout = timeout

        if not self._api_key:
            raise GetProntoError(
                "GetPronto API key is required. Set GETPRONTO_API_KEY "
                "in your environment or configure it in Wagtail Admin > "
                "Settings > Image Upload API Settings."
            )

    @property
    def _headers(self) -> dict[str, str]:
        token = self._token
        return {
            "ApiKey": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    @property
    def _token(self) -> str:
        """
        Obtain an authentication token using email/password.
        This is used for endpoints that require user-level auth.
        """
        cached_token = cache.get(TOKEN_CACHE_KEY)
        if cached_token:
            return cached_token

        email = get_api_email()
        password = get_api_password()
        if not email or not password:
            raise GetProntoAuthError(
                "GetPronto API email and password are required for this operation. "
                "Set GETPRONTO_EMAIL and GETPRONTO_PASSWORD in your environment or "
                "configure them in Wagtail Admin > Settings > Image Upload API Settings."
            )
        response = requests.post(
            self._url("/login"),
            json={"email": email, "password": password},
            timeout=self._timeout,
        )
        body = self._handle_response(response)
        token = body.get("jwt")
        if not token:
            raise GetProntoAuthError(
                "Authentication succeeded but no token was returned.",
                status_code=response.status_code,
            )
        cache.set(TOKEN_CACHE_KEY, token, TOKEN_CACHE_TIMEOUT)
        return token

    def _url(self, path: str) -> str:
        return f"{self._api_url}/{path.lstrip('/')}"

    def _handle_response(self, response: requests.Response) -> dict:
        """Parse a response, raising typed exceptions on error."""
        if response.status_code == 401 or response.status_code == 403:
            raise GetProntoAuthError(
                f"Authentication failed: {response.text}",
                status_code=response.status_code,
            )
        if response.status_code == 404:
            raise GetProntoNotFoundError(
                f"Resource not found: {response.text}",
                status_code=404,
            )
        if response.status_code == 429:
            raise GetProntoRateLimitError(
                f"Rate limit exceeded: {response.text}",
                status_code=429,
            )
        if not response.ok:
            raise GetProntoError(
                f"GetPronto API error ({response.status_code}): {response.text}",
                status_code=response.status_code,
            )

        # Some endpoints (e.g. image serving) return binary data
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return response.json()
        return {}

    def upload_file(
        self,
        file: IO[bytes],
        filename: str | None = None,
        custom_filename: str | None = None,
    ) -> ProntoFile:
        """Upload a file to GetPronto.

        Args:
            file: A file-like object opened for reading in binary mode.
            filename: The filename to send (used in the multipart upload).
            custom_filename: Optional custom filename stored on GetPronto.

        Returns:
            A ``ProntoFile`` with the uploaded file's metadata.
        """
        files: dict[str, Any] = {
            "file": (filename or "upload.png", file, ""),
        }
        data: dict[str, str] = {}
        if custom_filename:
            data["customFilename"] = custom_filename

        print(f"Uploading file to GetPronto: {filename or 'unnamed file'}")

        response = requests.post(
            self._url("/upload"),
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Length": f"{file.seek(0, io.SEEK_END)}",
            },  # Set Content-Length for file uploads
            files=files,
            data=data or None,
            timeout=self._timeout,
        )
        body = self._handle_response(response)
        return ProntoFile.from_api(body["file"])

    def list_files(self, page: int = 1, page_size: int = 20) -> ProntoFileList:
        """Retrieve a paginated list of files.

        Args:
            page: Page number (1-based).
            page_size: Items per page (max 100).
        """
        response = requests.get(
            self._url("/files"),
            headers=self._headers,
            params={"page": page, "pageSize": min(page_size, 100)},
            timeout=self._timeout,
        )
        body = self._handle_response(response)
        return ProntoFileList(
            files=[ProntoFile.from_api(f) for f in body.get("files", [])],
            pagination=(
                ProntoPagination.from_api(body["pagination"])
                if "pagination" in body
                else None
            ),
        )

    def get_file(self, file_id: str) -> ProntoFile:
        """Retrieve metadata for a single file by its ID."""
        response = requests.get(
            self._url(f"/files/{file_id}"),
            headers=self._headers,
            timeout=self._timeout,
        )
        body = self._handle_response(response)
        return ProntoFile.from_api(body["file"])

    def delete_file(self, file_id: str) -> None:
        """Permanently delete a file from GetPronto."""
        response = requests.delete(
            self._url(f"/files/{file_id}"),
            headers=self._headers,
            timeout=self._timeout,
        )
        self._handle_response(response)

    def get_image_url(
        self,
        path: str,
        *,
        w: int | None = None,
        h: int | None = None,
        fit: str | None = None,
        q: int | None = None,
        blur: float | None = None,
        sharp: bool | None = None,
        gray: bool | None = None,
        rot: int | None = None,
        border: str | None = None,
        crop: str | None = None,
    ) -> str:
        """Build a signed image URL with optional transformations.

        This constructs the URL locally — no API call is made.
        The resulting URL requires the ``ApiKey`` header when fetched.
        For public/pre-signed URLs use :meth:`generate_transform_url`.
        """
        params: dict[str, Any] = {}
        if w is not None:
            params["w"] = w
        if h is not None:
            params["h"] = h
        if fit:
            params["fit"] = fit
        if q is not None:
            params["q"] = q
        if blur is not None:
            params["blur"] = blur
        if sharp:
            params["sharp"] = "true"
        if gray:
            params["gray"] = "true"
        if rot is not None:
            params["rot"] = rot
        if border:
            params["border"] = border
        if crop:
            params["crop"] = crop

        url = self._url(f"/file/{path.lstrip('/')}")
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{qs}"
        return url

    def serve_image(
        self,
        path: str,
        **transform_kwargs,
    ) -> bytes:
        """Fetch raw image bytes with optional transformations.

        Keyword arguments are the same as :meth:`get_image_url`.
        """
        url = self.get_image_url(path, **transform_kwargs)
        response = requests.get(
            url,
            headers=self._headers,
            timeout=self._timeout,
        )
        if not response.ok:
            self._handle_response(response)
        return response.content

    def generate_transform_url(
        self,
        file_id: str,
        *,
        w: int | None = None,
        h: int | None = None,
        fit: str | None = None,
        q: int | None = None,
        blur: float | None = None,
        sharp: bool | None = None,
        gray: bool | None = None,
        rot: int | None = None,
        border: str | None = None,
        crop: str | None = None,
        fmt: str | None = None,
    ) -> TransformResult:
        """Generate a transform URL for an image via the API.

        Args:
            file_id: The unique identifier of the image on GetPronto.
            fmt: Output format (jpg, png, webp, etc.).
            **transform_kwargs: See GetPronto Images API docs.

        Returns:
            A ``TransformResult`` containing the generated URL and metadata.
        """
        payload: dict[str, Any] = {}
        if w is not None:
            payload["w"] = w
        if h is not None:
            payload["h"] = h
        if fit:
            payload["fit"] = fit
        if q is not None:
            payload["q"] = q
        if blur is not None:
            payload["blur"] = blur
        if sharp is not None:
            payload["sharp"] = sharp
        if gray is not None:
            payload["gray"] = gray
        if rot is not None:
            payload["rot"] = rot
        if border:
            payload["border"] = border
        if crop:
            payload["crop"] = crop
        if fmt:
            payload["format"] = fmt

        response = requests.post(
            self._url(f"/file/{file_id}/transform-url"),
            headers=self._headers,
            json=payload,
            timeout=self._timeout,
        )
        body = self._handle_response(response)

        original = None
        if "originalFile" in body:
            original = ProntoFile.from_api(body["originalFile"])

        return TransformResult(
            url=body["url"],
            original_file=original,
            transformations=body.get("transformations", {}),
        )

    @staticmethod
    def compress_image(
        file: IO[bytes],
        *,
        max_dimension: int = 1024,
        quality: int = DEFAULT_QUALITY,
        output_format: str = "WEBP",
    ) -> tuple[io.BytesIO, str]:
        """Compress and optionally resize an image in-memory.

        Args:
            file: A file-like object containing image data.
            max_dimension: The maximum width/height in pixels.
            quality: Output quality (1–100).
            output_format: Pillow format string (e.g. ``"WEBP"``, ``"JPEG"``).

        Returns:
            A tuple of ``(buffer, mime_type)`` with the compressed image
            data ready for upload.
        """
        img = Image.open(file)

        # Preserve orientation from EXIF
        try:
            from PIL import ImageOps

            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Convert RGBA to RGB for formats that don't support alpha
        if output_format.upper() in ("JPEG", "JPG") and img.mode in (
            "RGBA",
            "P",
        ):
            img = img.convert("RGB")

        # Resize if larger than max_dimension while preserving aspect ratio
        if max(img.size) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        buffer = io.BytesIO()
        save_kwargs: dict[str, Any] = {"quality": quality, "optimize": True}
        if output_format.upper() == "WEBP":
            save_kwargs["method"] = 4  # balance speed vs compression
        img.save(buffer, format=output_format, **save_kwargs)
        buffer.seek(0)

        mime_map = {
            "WEBP": "image/webp",
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "PNG": "image/png",
        }
        mime = mime_map.get(output_format.upper(), f"image/{output_format.lower()}")
        return buffer, mime
