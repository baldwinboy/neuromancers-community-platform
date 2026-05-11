from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdminGuideConfig(AppConfig):
    name = "neuromancers_network.admin_guide"
    verbose_name = _("Admin Guide")

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
