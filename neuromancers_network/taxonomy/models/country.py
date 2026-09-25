from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models import Timestamped


class Country(Timestamped):
    """An ISO 3166-1 alpha-2 country an admin has made selectable."""

    name = models.CharField(_("Name"), max_length=255, unique=True)
    code = models.CharField(
        _("ISO 3166-1 alpha-2 code"),
        max_length=2,
        unique=True,
    )
    sort_order = models.PositiveIntegerField(_("Sort order"), default=0)

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")
        ordering = ["-sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.code})"
