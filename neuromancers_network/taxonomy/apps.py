from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TaxonomyConfig(AppConfig):
    name = "neuromancers_network.taxonomy"
    verbose_name = _("Taxonomy")

    def ready(self):
        from .selectors import install_tag_group_filters  # noqa: PLC0415

        install_tag_group_filters()
