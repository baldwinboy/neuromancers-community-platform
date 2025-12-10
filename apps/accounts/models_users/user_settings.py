import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext as _
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from .user import User


class NotificationChoices(models.IntegerChoices):
    """
    Notifications may sent on the platform, via email, or not at all
    """

    NONE = 0, _("None")
    WEB_ONLY = 1, _("On this site")
    EMAIL = 2, _("Via email")
    ALL = 3, _("All")


class NotificationSubjectChoices(models.IntegerChoices):
    ACCOUNT = 0, _("Account")
    PAYMENT = 1, _("Payment")
    SESSION = 2, _("Session")
    REMINDER = 3, _("Reminder")


class Notifications(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sent_at = models.DateTimeField(auto_now=True)
    sent_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    subject = models.PositiveSmallIntegerField(
        choices=NotificationSubjectChoices,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    body = models.TextField(max_length=10_240)
    read = models.BooleanField(default=False)


# Notification settings for all users
class BaseNotificationSettings(models.Model):
    requested_session = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you request a session"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    responded_session = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification when a Care Provider has responded to your request"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    cancelled_session = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when your session is cancelled"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    session_reminders = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification before one (1) day and/or one (1) hour before your session starts"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    account_deleted = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when your account is deleted"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    payment_made = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you make a payment"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    payment_refunded = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when your payment is refunded"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )

    has_customized = models.BooleanField(default=False)

    class Meta:
        abstract = True


class NotificationSettings(BaseNotificationSettings):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="notification_settings",
        primary_key=True,
    )


class NotificationSettingsUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(NotificationSettings, on_delete=models.CASCADE)


class NotificationSettingsGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(NotificationSettings, on_delete=models.CASCADE)


# Notifications for Peer users
class PeerNotificationSettings(BaseNotificationSettings):
    published_session = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you publish a session"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    host_session_requested = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification when a Care Seeker requests a session from you"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    host_session_booked = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you accept a request"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    host_session_cancelled = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification when you or a Care Seeker cancel(s) a session"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    host_session_reminders = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification one (1) day and/or one (1) hour before a session provided by you starts"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    payment_received = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you receive a payment"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    payment_refund_request = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification when a Care Seeker requests a refund from you"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    payment_refunded = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you refund a payment"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="peer_notification_settings",
        primary_key=True,
    )


class PeerNotificationSettingsUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(
        PeerNotificationSettings, on_delete=models.CASCADE
    )


class PeerNotificationSettingsGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(
        PeerNotificationSettings, on_delete=models.CASCADE
    )


# Filters for Peer users
class PeerFilterSettings(models.Model):
    filters = models.JSONField(
        help_text=_("Your profile will be displayed under these filters when selected"),
        null=True,
        blank=True,
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="peer_filter_settings",
        primary_key=True,
    )


class PeerFilterSettingsUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(PeerFilterSettings, on_delete=models.CASCADE)


class PeerFilterSettingsGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(PeerFilterSettings, on_delete=models.CASCADE)
