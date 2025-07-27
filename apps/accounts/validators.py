import re

from django.conf import settings
from django.core.validators import MinLengthValidator, RegexValidator
from django.utils.translation import gettext as _

with open(settings.USERNAME_BANNED_WORDLIST) as f:
    USERNAME_BANNED_WORDS = set(line.strip().lower() for line in f if line.strip())
    username_banned_words_re = (
        r"(?i)^(.?)(?:"
        + "|".join(re.escape(word) for word in USERNAME_BANNED_WORDS)
        + r")(.?)$"
    )

username_safe_characters_re = r"^[\w-]+$"

username_no_banned_words = RegexValidator(
    regex=username_banned_words_re,
    inverse_match=True,
    message=_("A username must not contain certain words, i.e. 'admin'"),
    code="username_no_banned_words",
)

username_safe_characters = RegexValidator(
    regex=username_safe_characters_re,
    message=_(
        "A username may only contain alphanumeric characters (A-Z, 0-9), underscores (_), and dashes (-)"
    ),
    code="username_safe_characters",
)

username_min_length = MinLengthValidator(
    limit_value=5, message=_("A username must have at least five (5) characters")
)
