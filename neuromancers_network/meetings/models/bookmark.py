from django.db import models

from neuromancers_network.core.models import Timestamped


class MeetingsBookmark(Timestamped):
    meetings = models.ManyToManyField(
        "meetings.Meeting",
        related_name="bookmarks",
        blank=True,
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="meetings_bookmarks",
    )
