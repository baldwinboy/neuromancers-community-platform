from django.db import models
from django.utils.translation import gettext as _
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from .user import User


class Profile(models.Model):
    display_picture = models.ImageField(
        help_text=_("This image will be displayed on a user's profile"),
        null=True,
        blank=True,
    )
    about = models.TextField(
        help_text=_("This will be displayed on a user's profile as their summary"),
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

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
    )


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
