import re

from django.conf import settings
from django.core.validators import BaseValidator, MinLengthValidator, RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext as _

from .utils import calculate_age

username_banned_words_re = (
    r"(?i)^(.?)(?:"
    + "|".join(re.escape(word) for word in settings.ACCOUNT_USERNAME_BLACKLIST)
    + r")(.?)$"
)

username_safe_characters_re = r"^[\w-]+$"

username_banned_words_message = _("A username must not contain rude or banned words")

username_safe_characters_message = _(
    "A username may only contain alphanumeric characters (A-Z, 0-9), underscores (_), and dashes (-)"
)

username_min_length_message = _("A username must have at least five (5) characters")

name_banned_words_message = _("A name must not contain rude or banned words")

name_safe_characters_message = _(
    "A name may only contain alphanumeric characters (A-Z, 0-9), underscores (_), and dashes (-)"
)

username_no_banned_words = RegexValidator(
    regex=username_banned_words_re,
    inverse_match=True,
    message=username_banned_words_message,
    code="username_no_banned_words",
)

username_safe_characters = RegexValidator(
    regex=username_safe_characters_re,
    message=username_safe_characters_message,
    code="username_safe_characters",
)

username_min_length = MinLengthValidator(
    limit_value=5, message=username_min_length_message
)

username_validators = [
    username_min_length,
    username_safe_characters,
    username_no_banned_words,
]

name_no_banned_words = RegexValidator(
    regex=username_banned_words_re,
    inverse_match=True,
    message=name_banned_words_message,
    code="name_no_banned_words",
)

name_safe_characters = RegexValidator(
    regex=username_safe_characters_re,
    message=name_safe_characters_message,
    code="name_safe_characters",
)


@deconstructible
class MinAgeValidator(BaseValidator):
    message = _("You must be at least %(limit_value)d to use this platform")
    code = "min_age"

    def compare(self, a, b):
        return calculate_age(a) < b


user_over_18 = MinAgeValidator(18)
