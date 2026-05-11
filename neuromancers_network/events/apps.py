from django.apps import AppConfig
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _


class EventsConfig(AppConfig):
    name = "neuromancers_network.events"
    verbose_name = _("Events")

    def ready(self):
        from neuromancers_network.events.models import SessionBooking  # noqa: PLC0415

        from . import signals  # noqa: PLC0415
        from . import webhook_handlers  # noqa: PLC0415, F401

        post_save.connect(
            signals.log_booking_creation,
            sender=SessionBooking,
        )
