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
    link_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text=_("URL for the primary action associated with this notification"),
    )
    read = models.BooleanField(default=False)


# Notification settings for all users
class BaseNotificationSettings(models.Model):
    requested_session = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you request a session"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    responded_session = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification when a Care Provider has responded to your request"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    cancelled_session = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when your session is cancelled"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    session_reminders = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification before one (1) day and/or one (1) hour before your session starts"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    account_deleted = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when your account is deleted"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    payment_made = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you make a payment"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    payment_refunded = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when your payment is refunded"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
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
        default=NotificationChoices.ALL,
    )
    host_session_requested = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification when a Care Seeker requests a session from you"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    host_session_booked = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you accept a request"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    host_session_cancelled = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification when you or a Care Seeker cancel(s) a session"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    host_session_reminders = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification one (1) day and/or one (1) hour before a session provided by you starts"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    payment_received = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you receive a payment"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    payment_refund_request = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_(
            "You'll receive a notification when a Care Seeker requests a refund from you"
        ),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
    )
    payment_refunded = models.PositiveSmallIntegerField(
        choices=NotificationChoices,
        help_text=_("You'll receive a notification when you refund a payment"),
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        default=NotificationChoices.ALL,
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


# Privacy settings for Peer users
class PeerPrivacySettings(models.Model):
    """Controls what information is visible on a peer's public profile."""

    show_calendar = models.BooleanField(
        default=False,
        help_text=_(
            "If enabled, your availability calendar will be visible on your profile"
        ),
    )
    show_peer_session_details = models.BooleanField(
        default=False,
        help_text=_(
            "If enabled, titles and timing of peer sessions will be shown on your calendar"
        ),
    )
    show_group_session_details = models.BooleanField(
        default=True,
        help_text=_(
            "If enabled, non-sensitive details of group sessions will be shown on your calendar"
        ),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="peer_privacy_settings",
        primary_key=True,
    )


class PeerPrivacySettingsUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(PeerPrivacySettings, on_delete=models.CASCADE)


class PeerPrivacySettingsGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(PeerPrivacySettings, on_delete=models.CASCADE)
