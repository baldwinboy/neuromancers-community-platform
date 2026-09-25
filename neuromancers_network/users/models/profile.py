from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.search import index

from neuromancers_network.core.models import Timestamped

from .choices import ProfileVisibility


class UserProfile(index.Indexed, Timestamped):
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
    access_needs = models.TextField(
        _("Access needs"),
        blank=True,
        help_text=_("Free-text access needs shared with peers when booking."),
    )
    access_needs_visible_to_peer = models.BooleanField(
        _("Share access needs with peer"),
        default=True,
        help_text=_("Whether a peer may see your access needs ahead of a meeting."),
    )
    visibility = models.CharField(
        _("Visibility"),
        max_length=10,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.MEMBERS,
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
    country = models.CharField(
        _("Country"),
        max_length=2,
        blank=True,
        default="GB",
        help_text=_("ISO 3166-1 alpha-2 country code (used for Stripe Connect)."),
    )
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

    search_fields = [
        index.RelatedFields(
            "user",
            [
                index.SearchField("name"),
                index.SearchField("username"),
            ],
        ),
    ]

    def get_absolute_url(self) -> str:
        return self.user.get_absolute_url()
