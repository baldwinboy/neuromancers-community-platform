from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped
from neuromancers_network.core.storage import ExportsStorage


class ExportStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    READY = "ready", _("Ready")
    FAILED = "failed", _("Failed")


class DataExportRequest(Timestamped):
    """A member's request for a copy of their data (GDPR access/portability)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="data_exports",
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ExportStatus,
        default=ExportStatus.PENDING,
        db_index=True,
    )
    file = models.FileField(
        _("File"),
        upload_to="exports/",
        storage=ExportsStorage(),
        blank=True,
    )
    completed_at = models.DateTimeField(_("Completed at"), null=True, blank=True)
    expires_at = models.DateTimeField(_("Expires at"), null=True, blank=True)
    error = models.TextField(_("Error"), blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Data export request")
        verbose_name_plural = _("Data export requests")

    def __str__(self):
        return f"Data export #{self.pk} ({self.status})"
