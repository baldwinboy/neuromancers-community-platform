from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CommonConfig(AppConfig):
    name = "neuromancers_network.common"
    verbose_name = _("Common")

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
