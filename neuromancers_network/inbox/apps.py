from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InboxConfig(AppConfig):
    name = "neuromancers_network.inbox"
    label = "inbox"
    verbose_name = _("Inbox")

    def ready(self):
        """
        Connect the event bus to database events on startup.
        """
        from . import signals  # noqa: F401, PLC0415
