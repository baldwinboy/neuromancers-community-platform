from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped

from .choices import CalendarEventKind


class CalendarEvent(Timestamped):
    """A synthetic calendar entry for a peer's published calendar.

    One row per availability occurrence, booked 1:1 slot or public group
    meeting. Rows are kept in sync from their source objects by signals and are
    rendered through a viewer-aware queryset that redacts titles.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_events",
    )
    start = models.DateTimeField(_("Start"))
    end = models.DateTimeField(_("End"))
    kind = models.CharField(
        _("Kind"),
        max_length=20,
        choices=CalendarEventKind.choices,
        default=CalendarEventKind.AVAILABLE,
    )
    title = models.CharField(_("Title"), max_length=255, blank=True)
    is_public_detail = models.BooleanField(
        _("Publicly readable title"),
        default=False,
    )
    participant_ids = models.JSONField(
        _("Participant user ids"),
        default=list,
        blank=True,
        help_text=_("Users who may see the 1:1 title (only they and the owner)."),
    )
    source_type = models.CharField(_("Source type"), max_length=20, blank=True)
    source_id = models.PositiveBigIntegerField(_("Source id"), null=True, blank=True)

    class Meta:
        verbose_name = _("Calendar event")
        verbose_name_plural = _("Calendar events")
        ordering = ["start"]
        indexes = [
            models.Index(fields=["owner", "start"], name="peers_calendar_owner_start"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.start:%Y-%m-%d %H:%M} ({self.owner})"
