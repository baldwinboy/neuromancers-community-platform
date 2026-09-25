"""Concrete subscriber that forwards inbox events to daisIE EmailTemplates."""

from __future__ import annotations

import logging

from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet

from .subscriber import EventSubscriber

logger = logging.getLogger(__name__)


@register_snippet
class DaisieBridgeSubscriber(EventSubscriber):
    """Forward a recorded inbox event to the configured daisIE email bridge.

    One snippet per event type; the admin maps event keys to ``EmailTemplate``s
    via ``WAGTAIL_DAISIE_NOTIFICATION_BRIDGES``. Per-user opt-out is applied by
    the bridge's recipients builder.
    """

    class Meta(EventSubscriber.Meta):
        verbose_name = _("Daisie email bridge")
        verbose_name_plural = _("Daisie email bridges")

    def handle_event(self, log_entry):
        from wagtail_daisIE.notifications.bridges import (  # noqa: PLC0415
            UnknownBridgeError,
        )
        from wagtail_daisIE.notifications.bridges import dispatch  # noqa: PLC0415

        source = {
            "payload": log_entry.payload or {},
            "event_type": self.event_type,
            "log_entry": log_entry,
        }
        try:
            dispatch(
                self.event_type,
                source=source,
                event_ref=f"nel:{log_entry.pk}",
            )
        except UnknownBridgeError:
            logger.debug("No daisIE bridge configured for %s", self.event_type)
