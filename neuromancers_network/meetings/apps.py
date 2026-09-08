from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MeetingsConfig(AppConfig):
    name = "neuromancers_network.meetings"
    verbose_name = _("Meetings")

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
        from . import signals  # noqa: F401, PLC0415
