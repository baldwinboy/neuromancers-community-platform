"""
Concrete GetProntoImage and GetProntoRendition models.

These are what you set as WAGTAILIMAGES_IMAGE_MODEL.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.common.models import AbstractGetProntoImage
from neuromancers_network.common.models import AbstractGetProntoRendition


class GetProntoImage(AbstractGetProntoImage):
    """Concrete image model backed by GetPronto."""

    admin_form_fields = (
        "title",
        "file",
        "description",
        "collection",
        "tags",
    )

    class Meta(AbstractGetProntoImage.Meta):
        verbose_name = _("image")
        verbose_name_plural = _("images")
        permissions = [
            ("choose_image", "Can choose image"),
        ]


class GetProntoRendition(AbstractGetProntoRendition):
    """Concrete rendition model for GetProntoImage."""

    image = models.ForeignKey(
        GetProntoImage,
        on_delete=models.CASCADE,
        related_name="renditions",
    )

    class Meta(AbstractGetProntoRendition.Meta):
        abstract = False
