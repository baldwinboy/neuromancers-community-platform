import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped
from neuromancers_network.inbox.registry import register_subscriber_model

from .event_type import NotificationEventType

logger = logging.getLogger(__name__)


class EventSubscriber(Timestamped):
    """Abstract base for Wagtail-instantiable notification subscribers.

    A concrete subclass (registered with Wagtail, e.g. via ``@register_snippet``)
    represents "something that reacts to a specific event type". When the event
    bus records an event it calls ``handle_event`` on every active instance
    whose ``event_type`` matches.

    Concrete subclasses are expected to:

    * add whatever content/design fields admins will edit (templates with
      placeholders, channel configuration, ...);
    * implement ``handle_event(log_entry)`` to consume the recorded event.

    The base implementation only logs, so unconfigured subscribers are safe
    no-ops. No concrete subclass ships in application code on purpose: examples
    live in ``docs/notifications.rst`` and the test-suite only.
    """

    label = models.CharField(
        _("Label"),
        max_length=255,
        help_text=_("Human readable name shown in the Wagtail admin."),
    )
    event_type = models.CharField(
        _("Event type"),
        max_length=50,
        choices=NotificationEventType.choices,
        help_text=_("The event this subscriber reacts to."),
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        help_text=_(
            "Only active subscribers receive events from the bus.",
        ),
    )

    class Meta:
        abstract = True
        verbose_name = _("Event subscriber")
        verbose_name_plural = _("Event subscribers")

    def __str__(self):
        return self.label

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls._meta.abstract and cls._meta.app_config is not None:
            register_subscriber_model(cls)

    def handle_event(self, log_entry):
        """Called by the bus when the associated event is triggered.

        Parameters
        ----------
        log_entry : NotificationEventLog
            The recorded event with its normalized payload.

        Concrete subclasses override this. The default implementation only logs
        so that a subscriber with no behaviour yet is harmless.
        """
        reference = (
            f"#{log_entry.pk} ({log_entry.event_type})"
            if hasattr(log_entry, "pk")
            else str(log_entry)
        )
        logger.info("Subscriber %r received event %s", self.label, reference)
