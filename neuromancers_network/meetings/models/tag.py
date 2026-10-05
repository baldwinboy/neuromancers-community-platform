from django.db import models
from taggit.models import TaggedItemBase


class MeetingTag(TaggedItemBase):
    """Concrete taggit through-model restricting meeting tags to ``AllowedTag``."""

    content_object = models.ForeignKey(
        "meetings.Meeting",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        "taxonomy.AllowedTag",
        on_delete=models.CASCADE,
        related_name="meeting_items",
    )
