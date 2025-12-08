from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext as _


def validate_language_codes(value):
    """
    Validates that `value` is a comma-separated string of language codes
    where each code exists as the first item of a tuple in `languages`.

    Example:
        LANGUAGES = [('en', 'English'), ('fr', 'French')]
        validate_language_codes("en,fr")  # ok
        validate_language_codes("en,de")  # raises ValidationError
    """
    if not value:
        return  # Allow empty values; remove if required

    allowed_codes = [lang[0] for lang in settings.LANGUAGES]

    value = (
        str(value)
        .strip("[]")
        .replace(" ", "")
        .replace("'", "")
        .replace('"', "")
        .split(",")
    )

    codes = [code.strip() for code in value if code.strip()]

    invalid = [c for c in codes if c not in allowed_codes]

    if invalid:
        raise ValidationError(_("Invalid language"), code="invalid_lang")


slug_validator = RegexValidator(
    regex=r"^[-a-zA-Z0-9_]+$",
    message="Slug can only contain letters, numbers, hyphens, and underscores.",
)
