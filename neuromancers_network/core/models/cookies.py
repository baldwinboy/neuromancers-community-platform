"""Cookie registry used by the policy page and the consent banner."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped


class CookieCategory(models.TextChoices):
    NECESSARY = "necessary", _("Necessary")
    ANALYTICS = "analytics", _("Analytics")
    MARKETING = "marketing", _("Marketing")


class Cookie(Timestamped):
    """An admin-editable description of one cookie the site may set."""

    name = models.CharField(_("Name"), max_length=255, unique=True)
    provider = models.CharField(_("Provider"), max_length=255, blank=True)
    purpose = models.TextField(_("Purpose"), blank=True)
    duration = models.CharField(_("Duration"), max_length=100, blank=True)
    category = models.CharField(
        _("Category"),
        max_length=20,
        choices=CookieCategory,
        default=CookieCategory.NECESSARY,
        db_index=True,
    )
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        ordering = ["category", "name"]
        verbose_name = _("Cookie")
        verbose_name_plural = _("Cookies")

    def __str__(self):
        return self.name
