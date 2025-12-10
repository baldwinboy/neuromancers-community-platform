from django.db import models
from django.utils.translation import gettext as _
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from apps.accounts.utils import get_countries

from .user import User


class Profile(models.Model):
    display_picture = models.ImageField(
        help_text=_("This image will be displayed on your profile"),
        null=True,
        blank=True,
    )
    about = models.TextField(
        help_text=_(
            "Enter a short description. This will be displayed on your profile."
        ),
        null=True,
        blank=True,
    )
    access_needs = models.TextField(
        max_length=10_240,
        null=True,
        blank=True,
        help_text=_(
            "Care Providers will see this in your profile when you request a session"
        ),
    )

    terms_and_conditions = models.TextField(
        max_length=10_240,
        null=True,
        blank=True,
        help_text=_("Care Seekers will see this before requesting a session"),
    )

    country = models.CharField(
        max_length=2,
        choices=get_countries,
        help_text=_(
            "Where you currently decide. This will be displayed on your profile and in searches."
        ),
        null=True,
        blank=True,
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
    )

    has_customized = models.BooleanField(default=False)

    @property
    def country_display(self) -> str | None:
        if not self.country:
            return None

        all_countries = get_countries()
        return all_countries.get(self.country)


class ProfileUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Profile, on_delete=models.CASCADE)


class ProfileGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Profile, on_delete=models.CASCADE)


class Certificate(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="certificate",
        primary_key=True,
    )
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)


class CertificateUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Certificate, on_delete=models.CASCADE)


class CertificateGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Certificate, on_delete=models.CASCADE)


class StripeAccount(models.Model):
    id = models.CharField(unique=True, max_length=128)
    is_ready = models.BooleanField(default=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="stripe_account",
        primary_key=True,
    )


class StripeAccountUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(StripeAccount, on_delete=models.CASCADE)


class StripeAccountGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(StripeAccount, on_delete=models.CASCADE)
