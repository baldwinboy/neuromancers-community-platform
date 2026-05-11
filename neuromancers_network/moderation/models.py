from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.common.models.base import TimestampedModel


class ModeratedContentType(models.TextChoices):
    SESSION = "session", _("Session")
    REVIEW = "review", _("Review")
    MESSAGE = "message", _("Message")
    PROFILE = "profile", _("Profile")


class FlagReason(models.TextChoices):
    SPAM = "spam", _("Spam")
    ABUSIVE = "abusive", _("Abusive or harassing")
    INAPPROPRIATE = "inappropriate", _("Inappropriate content")
    MISINFORMATION = "misinformation", _("Misinformation")
    OTHER = "other", _("Other")


class FlagStatus(models.TextChoices):
    PENDING = "pending", _("Pending review")
    DISMISSED = "dismissed", _("Dismissed")
    UPHELD = "upheld", _("Upheld — content removed")
    ESCALATED = "escalated", _("Escalated to admin")


class FieldChoices(models.TextChoices):
    title = "title", _("Title")
    description = "description", _("Description")
    comment = "comment", _("Comment")


class Flag(TimestampedModel):
    """A user-generated flag on content that requires moderator review."""

    flagger = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="flags_made",
    )
    content_type = models.CharField(
        max_length=20,
        choices=ModeratedContentType.choices,
    )
    object_id = models.CharField(max_length=255)
    reason = models.CharField(
        max_length=30,
        choices=FlagReason.choices,
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=FlagStatus.choices,
        default=FlagStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="flags_reviewed",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Flag")
        verbose_name_plural = _("Flags")

    def __str__(self):
        return f"{self.get_content_type_display()} #{self.object_id} — {self.get_reason_display()}"


class FlagRule(TimestampedModel):
    """Auto-flagging rule based on keyword or pattern matching."""

    pattern = models.CharField(
        max_length=255,
        help_text=_("Keyword or regex pattern to match against"),
    )
    is_regex = models.BooleanField(
        default=False,
        help_text=_("Treat pattern as a regular expression"),
    )
    content_type = models.CharField(
        max_length=20,
        choices=ModeratedContentType.choices,
    )
    field = models.CharField(
        max_length=20,
        choices=FieldChoices.choices,
        default="description",
    )
    reason = models.CharField(
        max_length=30,
        choices=FlagReason.choices,
        default="inappropriate",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Flag Rule")
        verbose_name_plural = _("Flag Rules")

    def __str__(self):
        return f"{self.pattern} → {self.get_reason_display()}"
