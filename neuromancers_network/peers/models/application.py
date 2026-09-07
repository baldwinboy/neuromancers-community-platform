from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models import Timestamped

from .choices import PeerApplicationStatus


class PeerApplication(Timestamped):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="peer_application",
    )
    reason = models.TextField(_("Reason for applying"))
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=PeerApplicationStatus.choices,
        default=PeerApplicationStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_applications",
    )
    reviewed_at = models.DateTimeField(_("Reviewed at"), null=True, blank=True)
    submission = models.JSONField(_("Submission"), null=True, blank=True)

    class Meta:
        verbose_name_plural = "Peer applications"
