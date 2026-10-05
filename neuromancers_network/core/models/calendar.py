import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped


class CalendarFeedToken(Timestamped):
    """A per-user secret token for the read-only ICS calendar feed."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_feed_token",
    )
    token = models.UUIDField(
        _("Token"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Calendar feed token")
        verbose_name_plural = _("Calendar feed tokens")

    def __str__(self):
        return f"Calendar feed for {self.user}"
