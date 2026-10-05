"""Upload handlers for admin-authored daisIE form pages."""

from __future__ import annotations

from pathlib import PurePosixPath

from django.core.files.storage import default_storage


def store_document(*, page, form, field, file, request=None) -> str:
    """Store an uploaded document and return its public URL.

    Matches the daisIE upload-handler contract: called once per uploaded file
    with keyword-only ``page``, ``form``, ``field``, ``file`` and ``request``.
    """
    name = PurePosixPath(file.name).name
    stored = default_storage.save(f"form-uploads/{name}", file)
    return default_storage.url(stored)
