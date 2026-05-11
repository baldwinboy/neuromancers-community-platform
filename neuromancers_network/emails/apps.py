from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EmailsConfig(AppConfig):
    name = "neuromancers_network.emails"
    verbose_name = _("Emails")

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
