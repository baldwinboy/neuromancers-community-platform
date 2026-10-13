from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped

from .event_type import notification_event_choices


class Notification(Timestamped):
    """A per-recipient in-app notification materialised from the event bus."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_type = models.CharField(
        _("Event type"),
        max_length=50,
        choices=notification_event_choices,
        db_index=True,
    )
    title = models.CharField(_("Title"), max_length=255, blank=True)
    body = models.TextField(_("Body"), blank=True)
    link_url = models.CharField(_("Link"), max_length=500, blank=True)
    event_ref = models.CharField(
        _("Event reference"),
        max_length=255,
        blank=True,
        db_index=True,
    )
    read_at = models.DateTimeField(_("Read at"), null=True, blank=True)
    deleted_at = models.DateTimeField(_("Deleted at"), null=True, blank=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "read_at"],
                name="inbox_notif_recipient_read",
            ),
        ]

    def __str__(self):
        return f"{self.title or self.event_type} → {self.recipient}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self) -> None:
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at", "updated_at"])

    def soft_delete(self) -> None:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])
