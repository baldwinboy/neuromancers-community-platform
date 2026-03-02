"""
ImageKit mini-SDK

A lightweight Python client for the ImageKit REST API.
Mirrors the project's Stripe SDK pattern in apps/common/utils.py:
every public function accepts an optional ``request`` so that
Wagtail Admin overrides (ImageUploadSettings) take precedence
over values in django.conf.settings.

API reference: https://imagekit.io/docs/api-reference/upload-file/upload-file
SDK reference: https://github.com/imagekit-developer/imagekit-python
"""

from __future__ import annotations

import io
import logging
from typing import IO, Any

from django.conf import settings
from django.http import HttpRequest
from imagekitio import ImageKit
from imagekitio.types import FileUploadParams, FileUploadResponse, Metadata
from PIL import Image
from wagtail.contrib.settings.registry import registry

logger = logging.getLogger(__name__)

DEFAULT_URL_ENDPOINT = "https://ik.imagekit.io/your_imagekit_id"
DEFAULT_QUALITY = 85  # JPEG/WebP quality for compression
MAX_IMAGE_DIMENSION = 5000


def _load_image_upload_settings(request: HttpRequest):
    """
    Load ImageUploadSettings from the Wagtail registry.
    """
    return registry.get_by_natural_key("events", "ImageUploadSettings").load(
        request_or_site=request
    )


def get_private_key(request: HttpRequest | None = None) -> str:
    """
    Return the ImageKit private key.
    Checks Wagtail Admin ``ImageUploadSettings`` first when *request*
    is provided, then falls back to ``settings.IMAGEKIT_PRIVATE_KEY``.
    """
    if not request:
        return settings.IMAGEKIT_PRIVATE_KEY

    ws = _load_image_upload_settings(request)
    return ws.imagekit_private_key or settings.IMAGEKIT_PRIVATE_KEY


def get_public_key(request: HttpRequest | None = None) -> str:
    """
    Return the ImageKit public key.
    Checks Wagtail Admin ``ImageUploadSettings`` first when *request*
    is provided, then falls back to ``settings.IMAGEKIT_PUBLIC_KEY``.
    """
    if not request:
        return getattr(settings, "IMAGEKIT_PUBLIC_KEY", "")

    ws = _load_image_upload_settings(request)
    return ws.imagekit_public_key or getattr(settings, "IMAGEKIT_PUBLIC_KEY", "")


def get_url_endpoint(request: HttpRequest | None = None) -> str:
    """
    Return the ImageKit URL endpoint (without trailing slash).
    Checks Wagtail Admin ``ImageUploadSettings`` first when *request*
    is provided, then falls back to ``settings.IMAGEKIT_URL_ENDPOINT``.
    """
    if not request:
        base = getattr(settings, "IMAGEKIT_URL_ENDPOINT", DEFAULT_URL_ENDPOINT)
        return base.rstrip("/")

    ws = _load_image_upload_settings(request)
    base = ws.imagekit_url_endpoint or getattr(
        settings, "IMAGEKIT_URL_ENDPOINT", DEFAULT_URL_ENDPOINT
    )
    return base.rstrip("/")


class ImageKitError(Exception):
    """Base exception for ImageKit API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class ImageKitAuthError(ImageKitError):
    """Raised for authentication errors."""


class ImageKitNotFoundError(ImageKitError):
    """Raised when a resource is not found."""


class ImageKitClient:
    """Lightweight client for the ImageKit API.

    Usage::

        from apps.common.imagekit import ImageKitClient

        client = ImageKitClient(request=request)  # uses Wagtail settings
        result = client.upload_file(file_obj, filename="avatar.webp")
        print(result.url)
    """

    def __init__(
        self,
        *,
        private_key: str | None = None,
        public_key: str | None = None,
        url_endpoint: str | None = None,
        request: HttpRequest | None = None,
    ):
        self._private_key = private_key or get_private_key(request)
        self._public_key = public_key or get_public_key(request)
        self._url_endpoint = url_endpoint or get_url_endpoint(request)

        if not self._private_key:
            raise ImageKitError(
                "ImageKit private key is required. Set IMAGEKIT_PRIVATE_KEY "
                "in your environment or configure it in Wagtail Admin > "
                "Settings > Image Upload Settings."
            )

        self._client = ImageKit(
            private_key=self._private_key,
            public_key=self._public_key,
            url_endpoint=self._url_endpoint,
        )

    def upload_file(
        self,
        file: IO[bytes] | bytes,
        filename: str,
        folder: str = "/",
        tags: list[str] | None = None,
        use_unique_file_name: bool = True,
    ) -> FileUploadResponse:
        """Upload a file to ImageKit.

        Args:
            file: A file-like object or bytes containing the file data.
            filename: The filename to use for the uploaded file.
            folder: The folder path in ImageKit to upload to.
            tags: Optional list of tags to associate with the file.
            use_unique_file_name: Whether to append a unique suffix to the filename.

        Returns:
            An ``ImageKitFile`` with the uploaded file's metadata.
        """
        # Convert file-like object to bytes if needed
        if hasattr(file, "read"):
            file_data = file.read()
            if hasattr(file, "seek"):
                file.seek(0)
        else:
            file_data = file

        # Use the SDK's upload method
        options = FileUploadParams(
            folder=folder,
            tags=tags or [],
            use_unique_file_name=use_unique_file_name,
        )

        try:
            result = self._client.files.upload(
                file=file_data,
                file_name=filename,
                options=options,
            )

            return result

        except Exception as e:
            if isinstance(e, ImageKitError):
                raise
            raise ImageKitError(f"ImageKit upload failed: {e}")

    def delete_file(self, file_id: str) -> None:
        """Delete a file from ImageKit.

        Args:
            file_id: The unique identifier of the file to delete.
        """
        try:
            result = self._client.files.delete(file_id=file_id)

            if (
                hasattr(result, "response_metadata")
                and result.response_metadata.http_status_code >= 400
            ):
                raise ImageKitError(
                    f"Delete failed: {result.response_metadata.raw}",
                    status_code=result.response_metadata.http_status_code,
                )
        except Exception as e:
            if isinstance(e, ImageKitError):
                raise
            raise ImageKitError(f"ImageKit delete failed: {e}")

    def get_file_details(self, file_id: str) -> Metadata:
        """Get details of a file from ImageKit.

        Args:
            file_id: The unique identifier of the file.

        Returns:
            A ``Metadata`` object with the file's metadata.
        """
        try:
            result = self._client.files.metadata.get(file_id=file_id)

            if result.response_metadata.http_status_code >= 400:
                raise ImageKitNotFoundError(
                    f"File not found: {file_id}",
                    status_code=result.response_metadata.http_status_code,
                )

            return result
        except Exception as e:
            if isinstance(e, ImageKitError):
                raise
            raise ImageKitError(f"ImageKit get file details failed: {e}")

    def build_url(
        self,
        path: str,
        *,
        width: int | None = None,
        height: int | None = None,
        quality: int | None = None,
        format: str | None = None,
        crop: str | None = None,
        focus: str | None = None,
        blur: int | None = None,
        named_transformation: str | None = None,
    ) -> str:
        """Build a URL with transformations for an ImageKit file.

        Args:
            path: The file path or URL in ImageKit.
            width: Target width in pixels.
            height: Target height in pixels.
            quality: Output quality (1-100).
            format: Output format (webp, jpg, png, etc.).
            crop: Crop mode (maintain_ratio, force, at_max, at_least).
            focus: Focus area for cropping (auto, face, center, etc.).
            blur: Blur amount (1-100).
            named_transformation: A named transformation preset.

        Returns:
            The transformed image URL.
        """
        transformation = []

        if width is not None:
            transformation.append({"width": width})
        if height is not None:
            transformation.append({"height": height})
        if quality is not None:
            transformation.append({"quality": quality})
        if format is not None:
            transformation.append({"format": format})
        if crop is not None:
            transformation.append({"crop": crop})
        if focus is not None:
            transformation.append({"focus": focus})
        if blur is not None:
            transformation.append({"blur": blur})
        if named_transformation is not None:
            transformation.append({"named": named_transformation})

        # Flatten transformation list into single dict if needed
        if transformation:
            flat_transform = {}
            for t in transformation:
                flat_transform.update(t)
            transformation = [flat_transform]

        url = self._client.url(
            {
                "path": path,
                "transformation": transformation if transformation else None,
            }
        )
        return url

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


def get_imagekit_client(request: HttpRequest | None = None) -> ImageKitClient:
    """Get an ImageKitClient configured with appropriate settings.

    Args:
        request: Optional HTTP request for loading Wagtail admin settings.

    Returns:
        A configured ImageKitClient instance.
    """
    return ImageKitClient(request=request)
