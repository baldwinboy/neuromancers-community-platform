from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped


class UserBlock(Timestamped):
    """A one-way, member-to-member safety block.

    Blocking is pairwise: *blocker* no longer sees or interacts with *blocked*.
    Unblocking deletes the row.
    """

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_made",
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_received",
    )
    reason = models.TextField(_("Reason"), blank=True)

    class Meta:
        verbose_name = _("Member block")
        verbose_name_plural = _("Member blocks")
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="%(app_label)s_%(class)s_unique_block",
            ),
        ]

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"
