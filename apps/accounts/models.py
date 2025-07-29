from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext as _

from .validators import (
    username_banned_words_message,
    username_banned_words_re,
    username_min_length,
    username_no_banned_words,
    username_safe_characters,
    username_safe_characters_message,
    username_safe_characters_re,
)


# Users
# These are models that control users with specific groups
# Wagtail has a default management interface through the admin site: Settings > Users
# But this means creating the users for specific groups required every time the database is cleared
# Programmatic user types will allow for users with specific groups to be initialised wherever the project is deployed
class User(AbstractUser):
    display_picture = models.ImageField(
        help_text=_("This image will be displayed on a user's profile")
    )
    profile_bio = models.TextField(
        help_text=_("This will be displayed on a user's profile as their summary")
    )
    username = models.CharField(
        unique=True,
        max_length=64,
        validators=[
            AbstractUser.username_validator,
            username_min_length,
            username_no_banned_words,
            username_safe_characters,
        ],
    )
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.CheckConstraint(
                condition=~Q(username__regex=username_banned_words_re),
                name="username_no_banned_words_check",
                violation_error_message=username_banned_words_message,
            ),
            models.CheckConstraint(
                condition=Q(username__regex=username_safe_characters_re),
                name="username_safe_characters_check",
                violation_error_message=username_safe_characters_message,
            ),
        ]

    def __str__(self):
        return self.username
