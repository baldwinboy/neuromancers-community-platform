from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped

from .event_type import NotificationEventType

_DISPLAY_MAX_CHARS = 60


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

    @property
    def disabled_event_types_display(self) -> str:
        """Comma-separated human labels for the opt-out list (for admin lists)."""
        labels = [
            str(NotificationEventType(value).label)
            for value in self.disabled_event_types or []
            if value in NotificationEventType.values
        ]
        if not labels:
            return "—"
        joined = ", ".join(labels)
        if len(joined) > _DISPLAY_MAX_CHARS:
            return f"{joined[: _DISPLAY_MAX_CHARS - 1]}…"
        return joined
