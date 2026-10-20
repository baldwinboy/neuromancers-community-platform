"""Upload validators and the registered daisIE form-field types."""

from __future__ import annotations

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from wagtail_daisIE.forms.registry import get_form_field_types
from wagtail_daisIE.forms.registry import reset_form_field_types

from neuromancers_network.core.validators import validate_image


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def test_validate_image_accepts_png():
    upload = SimpleUploadedFile("photo.png", _png_bytes(), content_type="image/png")

    validate_image(upload)


def test_validate_image_rejects_non_image():
    upload = SimpleUploadedFile("notes.txt", b"not an image")

    with pytest.raises(ValidationError):
        validate_image(upload)


def test_registered_form_field_types_resolve():
    reset_form_field_types()
    try:
        types = get_form_field_types()
        assert "attachments" in types
        assert "autocomplete" in types
        assert types["attachments"].is_upload is True
        assert types["attachments"].multiple is True
    finally:
        reset_form_field_types()
