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
    bio = models.TextField(_("Bio"), blank=True)
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
    # Named access-needs templates: [{"name": ..., "body": ...}]
    access_needs_templates = models.JSONField(
        _("Access needs templates"),
        default=list,
        blank=True,
        help_text=_("Named access-needs templates, each with a name and body."),
    )
    visibility = models.CharField(
        _("Visibility"),
        max_length=10,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.MEMBERS,
    )

    # Calendar visibility (peers publish their calendar explicitly)
    show_calendar = models.BooleanField(
        _("Publish my calendar"),
        default=False,
        help_text=_("Let other members see your availability and booked slots."),
    )
    show_peer_meeting_details = models.BooleanField(
        _("Show 1:1 meeting titles"),
        default=False,
        help_text=_("Show 1:1 titles on your calendar (readers always see times)."),
    )
    show_group_meeting_details = models.BooleanField(
        _("Show group meeting titles"),
        default=True,
        help_text=_("Show public group meeting titles on your calendar."),
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
        index.SearchField("bio"),
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
