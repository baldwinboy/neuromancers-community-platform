from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NotificationsConfig(AppConfig):
    name = "neuromancers_network.notifications"
    verbose_name = _("Notifications")

    def ready(self):
        """
        Connect the event bus to database events on startup.
        """
        from . import signals  # noqa: F401, PLC0415
