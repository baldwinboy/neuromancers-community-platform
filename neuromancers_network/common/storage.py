"""
Django storage backend for GetPronto with runtime API key loading.

The API key can be passed as:
- a plain string,
- a callable (e.g. a lambda or function) that returns the key,
- or left to the default fallback which checks:
    1. the `GETPRONTO_API_KEY` Django setting (string)
    2. the `GETPRONTO_API_KEY_GETTER` Django setting (dotted path to a callable)
"""

import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING

from django.apps import apps
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from . import getpronto as api

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def _default_key_resolver() -> str | None:
    """
    Default way to obtain a GetPronto API key at runtime.

    Loads from Wagtail settings. Returns ``None`` if nothing is configured.
    """
    try:
        ExternalAPISettings = apps.get_model("core", "ExternalAPISettings")
        settings = ExternalAPISettings.load()
    except Exception:
        logger.exception("Failed to load API key via GETPRONTO_API_KEY_GETTER")
        return None

    return settings.getpronto_api_key


@deconstructible
class GetProntoStorage(Storage):
    """
    Storage backend that saves files to GetPronto via the three-step upload
    flow and retrieves them via the secure (authenticated) URL.

    :param api_key: API key **string** or a **callable** returning a string.
        If omitted, the default resolver (``_default_key_resolver``) is used,
        which consults ``GETPRONTO_API_KEY`` and ``GETPRONTO_API_KEY_GETTER``.
    """

    def __init__(
        self,
        api_key: str | Callable[[], str] | None = None,
    ):
        # Store the raw value; resolving is done lazily via _resolve_api_key()
        if api_key is None:
            api_key = _default_key_resolver
        self._api_key_or_callable = api_key
        # Cache the resolved value for the duration of a request/response?
        # We leave it uncached so that each call gets the freshest key.
        # If performance is an issue, a short-lived cache can be added.

    # ------------------------------------------------------------------
    # Internal key resolution
    # ------------------------------------------------------------------

    def _resolve_api_key(self) -> str:
        """Return the API key, calling the callable if necessary."""
        val = self._api_key_or_callable
        if isinstance(val, str):
            return val
        if callable(val):
            key = val()
            if not key:
                msg = "GetProntoStorage: API key callable returned an empty key."
                raise ValueError(
                    msg,
                )
            return key
        msg = "GetProntoStorage: invalid API key type; expected str or callable."
        raise ValueError(
            msg,
        )

    def get_api_key(self) -> str:
        """Public accessor for the currently resolved API key."""
        return self._resolve_api_key()

    # ------------------------------------------------------------------
    # Required Storage API
    # ------------------------------------------------------------------

    def _open(self, name: str, mode: str = "rb") -> ContentFile:
        """Retrieve a file's content from GetPronto."""
        key = self._resolve_api_key()
        info = api.get_file(key, name)  # name == GetPronto file id
        resp = api.requests.get(info.secure_url, headers=api._headers(key))
        if not resp.ok:
            msg = f"Failed to fetch file {name}: {resp.status_code}"
            raise api.GetProntoError(msg)
        return ContentFile(resp.content, name=info.name)

    def _save(self, name: str, content) -> str:
        """Execute the three-step upload flow and return the file ID."""
        key = self._resolve_api_key()
        content.seek(0, os.SEEK_END)
        size = content.tell()
        content.seek(0)
        original_name = name
        mimetype = getattr(content, "content_type", None) or "application/octet-stream"

        # Step 1
        upload = api.PresignedUploadRequest(
            filename=original_name,
            mimetype=mimetype,
            size=size,
        )
        presigned = api.request_presigned_url(
            api_key=key,
            upload=upload,
        )
        # Step 2
        api.upload_to_storage(presigned.presigned_url, content)
        # Step 3
        file_info = api.confirm_upload(key, presigned.pending_upload_id)
        logger.info("Saved file '%s' as GetPronto id=%s", original_name, file_info.id)
        return file_info.id

    def delete(self, name: str) -> None:
        api.delete_file(self._resolve_api_key(), name)

    def exists(self, name: str) -> bool:
        try:
            api.get_file(self._resolve_api_key(), name)
        except api.GetProntoError:
            return False
        return True

    def url(self, name: str) -> str:
        """Return the secure (authenticated) URL for the file."""
        key = self._resolve_api_key()
        if not hasattr(self, "_url_cache"):
            self._url_cache = {}
        if name not in self._url_cache:
            info = api.get_file(key, name)
            self._url_cache[name] = info.secure_url
        return self._url_cache[name]

    def size(self, name: str) -> int:
        info = api.get_file(self._resolve_api_key(), name)
        return info.raw_size

    def get_modified_time(self, name: str):

        info = api.get_file(self._resolve_api_key(), name)
        return datetime.fromisoformat(info.raw_updated)
