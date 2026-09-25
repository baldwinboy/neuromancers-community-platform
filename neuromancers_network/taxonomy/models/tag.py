from django.db import models
from django.utils.translation import gettext_lazy as _
from taggit.models import TagBase


class AllowedTag(TagBase):
    """A tag an admin has explicitly allowed, always inside a :class:`TagGroup`."""

    group = models.ForeignKey(
        "taxonomy.TagGroup",
        on_delete=models.PROTECT,
        related_name="tags",
        verbose_name=_("Group"),
    )
    description = models.TextField(_("Description"), blank=True)
    sort_order = models.PositiveIntegerField(_("Sort order"), default=0)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Allowed tag")
        verbose_name_plural = _("Allowed tags")
        ordering = ["group", "-sort_order", "name"]
        indexes = [
            models.Index(
                fields=["group", "is_active"],
                name="taxonomy_tag_group_active_idx",
            ),
        ]

    def __str__(self):
        return self.name
