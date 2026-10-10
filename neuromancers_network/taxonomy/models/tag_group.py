from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models import Timestamped


class TagGroup(Timestamped):  # type: ignore[django-manager-missing]
    """A curator-defined grouping of allowed tags (e.g. "lived experience")."""

    name = models.CharField(_("Name"), max_length=255, unique=True)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True)
    sort_order = models.IntegerField(_("Sort order"), null=True, blank=True)
    sort_order_field = "sort_order"
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Tag group")
        verbose_name_plural = _("Tag groups")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:255]
        super().save(*args, **kwargs)
