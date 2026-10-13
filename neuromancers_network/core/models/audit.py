from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import Timestamped


class AccountAuditLog(Timestamped):
    """Append-only record of sensitive account and moderation actions.

    Rows are written by account/moderation services (via
    ``neuromancers_network.core.audit.record_audit``) and must never be
    updated or deleted, so there is a transparent, ordered trail of who did
    what, to whom, when, and from where.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_audit_actions",
        help_text=_("The member who performed the action, if any."),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_audit_entries",
        help_text=_("The member the action was performed on, if any."),
    )
    action = models.CharField(_("Action"), max_length=64, db_index=True)
    event_type = models.CharField(_("Event type"), max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(
        _("IP address"),
        null=True,
        blank=True,
    )
    user_agent = models.CharField(_("User agent"), max_length=255, blank=True)
    changes = models.JSONField(_("Changes"), default=dict, blank=True)
    reason = models.TextField(_("Reason"), blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Account audit log")
        verbose_name_plural = _("Account audit logs")
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="acct_audit_user_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.action} @ {self.created_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            message = "Account audit entries are append-only and cannot be modified."
            raise ValueError(message)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        message = "Account audit entries cannot be deleted."
        raise ValueError(message)
