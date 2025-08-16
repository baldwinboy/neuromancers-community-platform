import datetime

from django.contrib.auth.models import AbstractBaseUser, Group, UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from guardian.mixins import GuardianGroupMixin, GuardianUserMixin
from guardian.models import GroupObjectPermissionAbstract, UserObjectPermissionAbstract
from guardian.shortcuts import get_objects_for_user

from .mixins import UserGroupPermissionsMixin
from .validators import (
    username_min_length,
    username_safe_characters,
    username_safe_characters_message,
    username_safe_characters_re,
)


# Custom Group with Django Guardian for object-level permissions
class UserGroup(Group, GuardianGroupMixin):
    label = models.CharField(max_length=120)


# Users
# These are models that control users with specific groups
# Wagtail has a default management interface through the admin site: Settings > Users
# But this means creating the users for specific groups required every time the database is cleared
# Programmatic user types will allow for users with specific groups to be initialised wherever the project is deployed
class User(AbstractBaseUser, GuardianUserMixin, UserGroupPermissionsMixin):
    username_validator = UnicodeUsernameValidator()

    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email = models.EmailField(_("email address"), blank=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

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
            username_validator,
            username_min_length,
            username_safe_characters,
        ],
    )
    date_of_birth = models.DateField(null=True, blank=True)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.CheckConstraint(
                condition=Q(username__regex=username_safe_characters_re),
                name="username_safe_characters_check",
                violation_error_message=username_safe_characters_message,
            ),
        ]

    def __str__(self):
        return self.username

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = "{} {}".format(self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    @property
    def get_hosted_sessions(self):
        perms = [
            ["events.change_peersession", "events.delete_peersession"],
            ["events.change_groupsession", "events.delete_groupsession"],
        ]

        return [
            obj
            for perm in perms
            for obj in get_objects_for_user(self, perm, accept_global_perms=False)
        ]


class BigUserObjectPermission(UserObjectPermissionAbstract):
    class Meta(UserObjectPermissionAbstract.Meta):
        abstract = False
        indexes = [
            *UserObjectPermissionAbstract.Meta.indexes,
            models.Index(fields=["content_type", "object_pk", "user"]),
        ]


class BigGroupObjectPermission(GroupObjectPermissionAbstract):
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)

    class Meta(GroupObjectPermissionAbstract.Meta):
        abstract = False
        indexes = [
            *GroupObjectPermissionAbstract.Meta.indexes,
            models.Index(fields=["content_type", "object_pk", "group"]),
        ]


def get_anonymous_user_instance(User):
    return User(
        username="nonny",
        date_of_birth=datetime.date(1970, 1, 1),
    )
