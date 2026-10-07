from django.db import models
from taggit.models import TaggedItemBase


class StandardPageTag(TaggedItemBase):
    """Concrete taggit through-model restricting page tags to ``AllowedTag``."""

    content_object = models.ForeignKey(
        "core.StandardPage",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        "taxonomy.AllowedTag",
        on_delete=models.CASCADE,
        related_name="standard_page_items",
    )
