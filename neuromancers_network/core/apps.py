from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = "neuromancers_network.core"
    verbose_name = _("Core")

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
