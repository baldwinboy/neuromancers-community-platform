from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped


class SupportKind(models.TextChoices):
    REPORT_USER = "report_user", _("Report a member")
    REPORT_MEETING = "report_meeting", _("Report a meeting")
    REPORT_REVIEW = "report_review", _("Report a review")
    GENERAL = "general", _("General enquiry")


class SupportStatus(models.TextChoices):
    OPEN = "open", _("Open")
    IN_REVIEW = "in_review", _("In review")
    RESOLVED = "resolved", _("Resolved")
    REJECTED = "rejected", _("Rejected")


class SupportTicket(Timestamped):
    """A member-submitted report or support request.

    Created by an admin-authored ``SupportFormPage`` (a DaisyUI form), reviewed
    from the Operations Moderation queue.
    """

    kind = models.CharField(
        _("Kind"),
        max_length=20,
        choices=SupportKind,
        default=SupportKind.GENERAL,
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
    )
    subject_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets_about",
        help_text=_("The member the ticket is about, if any."),
    )
    subject_url = models.URLField(
        _("Subject link"),
        blank=True,
        help_text=_("Optional link to the reported meeting/review."),
    )
    message = models.TextField(_("Message"), blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=SupportStatus,
        default=SupportStatus.OPEN,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_tickets",
    )
    response = models.TextField(_("Response"), blank=True)
    resolved_at = models.DateTimeField(_("Resolved at"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Support ticket")
        verbose_name_plural = _("Support tickets")

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk} ({self.status})"
