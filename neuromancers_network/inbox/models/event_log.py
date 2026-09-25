from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped

from .event_type import NotificationEventType


class NotificationEventLog(Timestamped):
    """One row per business event recorded by the event bus.

    Acts as the internal "webhook source": every relevant database event
    appends a row here with a snapshot of the context needed to render a
    notification later. Nothing is sent to users by this model itself; it is
    the durable store that (future) notification channels and Wagtail-configured
    subscribers consume.

    ``payload`` uses a normalized shape so consumers can rely on stable keys::

        {
            "actor_user_id": <int|None>,
            "recipient_user_ids": [<int>, ...],
            "object_type": "meetingrequest" | "refundrequest" | ...,
            "object_id": <int|None>,
            "meta": { ... domain specific snapshot ... },
        }

    ``event_ref`` is a stable, per-object dedupe key (e.g.
    ``"meetingrequest.42.cancelled"``) used to keep scheduled emissions
    idempotent.
    """

    event_type = models.CharField(
        _("Event type"),
        max_length=50,
        choices=NotificationEventType.choices,
        db_index=True,
    )
    payload = models.JSONField(_("Payload"), default=dict, blank=True)
    event_ref = models.CharField(
        _("Event reference"),
        max_length=255,
        blank=True,
        db_index=True,
        help_text=_(
            "Stable reference used to dedupe events, e.g. meetingrequest.42.cancelled.",
        ),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        default="recorded",
        choices=[
            ("recorded", _("Recorded")),
            ("delivered", _("Delivered")),
            ("failed", _("Failed")),
        ],
        help_text=_(
            "Delivery state reserved for future notification channels.",
        ),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Notification event log")
        verbose_name_plural = _("Notification event logs")
        indexes = [
            models.Index(
                fields=["event_type", "event_ref"],
                name="notif_event_type_ref_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.created_at:%Y-%m-%d %H:%M:%S})"
