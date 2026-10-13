from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped


class DeletionStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    CANCELLED = "cancelled", _("Cancelled")
    COMPLETED = "completed", _("Completed")


class AccountDeletionRequest(Timestamped):
    """A member's request to delete (anonymise) their account after a grace period.

    The account is deactivated immediately and can be cancelled during the
    grace window. Purge anonymises the member in place rather than deleting the
    row, so financial records keep their foreign keys.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deletion_request",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deletion_requests_made",
        help_text=_("The member who asked for the deletion (self or a moderator)."),
    )
    reason = models.TextField(_("Reason"), blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=DeletionStatus,
        default=DeletionStatus.PENDING,
        db_index=True,
    )
    scheduled_for = models.DateTimeField(_("Scheduled for"), db_index=True)
    completed_at = models.DateTimeField(_("Completed at"), null=True, blank=True)

    class Meta:
        ordering = ["scheduled_for"]
        verbose_name = _("Account deletion request")
        verbose_name_plural = _("Account deletion requests")

    def __str__(self):
        return f"Deletion of user {self.user_id} ({self.status})"


class DeletedIdentity(Timestamped):
    """Hashed identity of a purged account, kept to enforce re-registration cooldowns.

    Only keyed hashes are stored, never the original address or username.
    """

    email_hash = models.CharField(_("Email hash"), max_length=64, db_index=True)
    username_hash = models.CharField(
        _("Username hash"),
        max_length=64,
        db_index=True,
    )
    purge_after = models.DateTimeField(_("Purge after"), db_index=True)

    class Meta:
        verbose_name = _("Deleted identity")
        verbose_name_plural = _("Deleted identities")

    def __str__(self):
        return f"Deleted identity (purge after {self.purge_after:%Y-%m-%d})"
