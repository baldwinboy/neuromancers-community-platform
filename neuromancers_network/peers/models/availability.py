from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped


class PeerAvailability(Timestamped):
    """
    Represents a blocked time window during which a peer does NOT want
    to receive 1:1 meeting requests. The system uses these blocks to
    reject requests whose requested_start_time falls within any block.
    """

    peer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_blocks",
    )
    start = models.DateTimeField(_("Start of unavailable window"))
    end = models.DateTimeField(_("End of unavailable window"))
    reason = models.CharField(
        _("Reason"),
        max_length=255,
        blank=True,
        help_text=_("Optional reason for blocking this time window."),
    )

    class Meta:
        verbose_name = "Peer availability block"
        verbose_name_plural = "Peer availability blocks"
        ordering = ["start"]

    def __str__(self):
        return f"Blocked: {self.start} - {self.end}"

    def clean(self):
        super().clean()
        if self.end <= self.start:
            raise ValidationError(_("End time must be after start time."))

    def overlaps(self, start, end):
        """Return True if [start, end) overlaps with this block."""
        return self.start < end and start < self.end
