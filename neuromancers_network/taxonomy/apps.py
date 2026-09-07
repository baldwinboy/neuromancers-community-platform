from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TaxonomyConfig(AppConfig):
    name = "neuromancers_network.taxonomy"
    verbose_name = _("Taxonomy")

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
