"""Upload validators for admin-authored daisIE form pages.

The daisIE form-field registry runs ``validators`` once per uploaded file and
``collection_validators`` once on the whole value. These helpers are referenced
by dotted path from ``WAGTAIL_DAISIE_FORM_FIELD_TYPES``; the package itself
ships no validators.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile


def validate_image(file: UploadedFile) -> None:
    """Reject anything Pillow cannot open as an image.

    Used as a per-file validator. It imposes no size or dimension limits — those
    are left to the admin to configure on the field type.
    """
    from PIL import Image  # noqa: PLC0415

    try:
        image = Image.open(file)
        image.verify()
    except (OSError, ValueError) as exc:
        message = _("Upload a valid image file.")
        raise ValidationError(message) from exc
    finally:
        file.seek(0)
