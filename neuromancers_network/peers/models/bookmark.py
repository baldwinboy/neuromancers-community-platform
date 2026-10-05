from django.db import models

from neuromancers_network.core.models import Timestamped


class PeersBookmark(Timestamped):
    peers = models.ManyToManyField(
        "peers.PeerProfile",
        related_name="bookmarks",
        blank=True,
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="peers_bookmarks",
    )
