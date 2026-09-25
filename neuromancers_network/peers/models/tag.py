from django.db import models
from taggit.models import TaggedItemBase


class PeerProfileTag(TaggedItemBase):
    """Concrete taggit through-model restricting peer tags to ``AllowedTag``."""

    content_object = models.ForeignKey(
        "peers.PeerProfile",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        "taxonomy.AllowedTag",
        on_delete=models.CASCADE,
        related_name="peer_profile_items",
    )
