from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped

from .choices import AvailabilityOccurrence


class PeerAvailability(Timestamped):
    """A window of time a peer is available for 1:1 meeting requests.

    Windows may be one-off or recurring (daily/weekly/monthly) across an
    occurrence range. Requests are only accepted inside a window; the slot
    expansion lives in ``peers.services.available_slots``.
    """

    peer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_windows",
    )
    start = models.DateTimeField(_("Available from"))
    end = models.DateTimeField(_("Available until"))
    occurrence = models.CharField(
        _("Repeats"),
        max_length=10,
        choices=AvailabilityOccurrence.choices,
        blank=True,
        default=AvailabilityOccurrence.NONE,
    )
    occurrence_starts_at = models.DateTimeField(
        _("Repeats from"),
        null=True,
        blank=True,
        help_text=_("Start of the recurring range. Defaults to now."),
    )
    occurrence_ends_at = models.DateTimeField(
        _("Repeats until"),
        null=True,
        blank=True,
        help_text=_("End of the recurring range. Defaults to one year from now."),
    )
    reason = models.CharField(
        _("Note"),
        max_length=255,
        blank=True,
        help_text=_("Optional note shown to the peer, e.g. 'evenings'."),
    )

    class Meta:
        verbose_name = _("Availability window")
        verbose_name_plural = _("Availability windows")
        ordering = ["start"]

    def __str__(self):
        return f"{self.start:%Y-%m-%d %H:%M} - {self.end:%H:%M} ({self.peer})"

    def clean(self):
        super().clean()
        if self.start and self.end and self.end <= self.start:
            raise ValidationError(_("End time must be after start time."))
        if (
            self.occurrence
            and self.occurrence_starts_at
            and self.occurrence_ends_at
            and self.occurrence_ends_at < self.occurrence_starts_at
        ):
            raise ValidationError(_("Repeat end must be after repeat start."))

    def overlaps(self, start, end) -> bool:
        """Return True when ``[start, end)`` overlaps this window."""
        return self.start < end and start < self.end

    def contains(self, start, end) -> bool:
        """Return True when ``[start, end)`` fits entirely inside this window."""
        return self.start <= start and end <= self.end
