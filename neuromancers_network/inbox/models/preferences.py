from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped


class NotificationPreference(Timestamped):
    """Per-user opt-out list of notification event types."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    disabled_event_types = models.JSONField(
        _("Disabled event types"),
        default=list,
        blank=True,
        help_text=_("Event types this member has opted out of."),
    )

    class Meta:
        verbose_name = _("Notification preference")
        verbose_name_plural = _("Notification preferences")

    def __str__(self):
        return f"Notification preferences for {self.user}"
