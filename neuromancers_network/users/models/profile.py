from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models import Timestamped


class UserProfile(Timestamped):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_profile",
    )

    # Profile picture — uploaded via getpronto, stored as URL
    profile_picture_url = models.URLField(
        _("Profile picture URL"),
        blank=True,
        help_text=_("Uploaded via getpronto. Set by the upload flow."),
    )
    profile_picture_getpronto_id = models.CharField(
        _("Getpronto file ID"),
        max_length=255,
        blank=True,
        db_index=True,
    )
    support_needs = models.TextField(
        _("Support needs"),
        blank=True,
        help_text=_("Free-text support needs."),
    )

    # Notification preferences
    notify_meeting_request = models.BooleanField(
        _("Meeting request alerts"),
        default=True,
    )
    notify_meeting_approved = models.BooleanField(
        _("Meeting approved alerts"),
        default=True,
    )
    notify_meeting_reminder = models.BooleanField(
        _("Meeting reminder alerts"),
        default=True,
    )
    notify_review_received = models.BooleanField(
        _("Review received alerts"),
        default=True,
    )
    notify_refund_request = models.BooleanField(
        _("Refund request alerts"),
        default=True,
    )
    notify_peer_application_update = models.BooleanField(
        _("Peer application update alerts"),
        default=True,
    )
    notify_platform_announcements = models.BooleanField(
        _("Platform announcements"),
        default=True,
    )

    # Preferences
    timezone = models.CharField(
        _("Timezone"),
        max_length=50,
        default="UTC",
        blank=True,
    )
    languages = models.ManyToManyField(
        "taxonomy.Language",
        blank=True,
        related_name="user_profiles",
    )
