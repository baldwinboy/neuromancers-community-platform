from django.conf import settings
from django.db import models
from django.utils import timezone
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
    is_approved = models.BooleanField(
        _("Approved"),
        default=False,
        help_text=_("Mirrors the approved status; toggling either keeps both in sync."),
    )
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

    def __str__(self):
        return f"{self.user} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Keep `is_approved` and `status` in sync: approval via either field wins.
        if self.is_approved or self.status == PeerApplicationStatus.APPROVED:
            self.is_approved = True
            self.status = PeerApplicationStatus.APPROVED
        elif self.status == PeerApplicationStatus.REJECTED:
            self.is_approved = False
        super().save(*args, **kwargs)

    def approve(self, reviewer=None):
        """Approve the application and mark the applicant's peer profile."""
        from neuromancers_network.peers.models.profile import (  # noqa: PLC0415
            PeerProfile,
        )

        self.is_approved = True
        self.status = PeerApplicationStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()

        profile, _created = PeerProfile.objects.get_or_create(user=self.user)
        profile.is_approved = True
        profile.approved_by = reviewer
        profile.approved_at = self.reviewed_at
        profile.save()
        return profile

    def reject(self, reviewer=None):
        """Reject the application."""
        self.is_approved = False
        self.status = PeerApplicationStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
