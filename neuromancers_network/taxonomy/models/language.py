from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models import Timestamped


class Language(Timestamped):
    name = models.CharField(_("Name"), max_length=256, unique=True)
    name_local = models.CharField(_("Local name"), max_length=256, unique=True)
    code = models.CharField(_("ISO 639-1 code"), max_length=2, unique=True)
    sort_order = models.PositiveIntegerField(
        _("Sort order"),
        default=0,
        help_text=_("Languages with higher sort order are displayed first."),
    )

    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")
        ordering = ["-sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.code})"
