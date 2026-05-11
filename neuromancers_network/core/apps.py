from django.apps import AppConfig
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = "neuromancers_network.core"
    verbose_name = _("Core")

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
        from neuromancers_network.core.models import ExternalAPISettings

        from . import signals  # noqa: PLC0415

        post_save.connect(
            signals.update_dj_stripe_keys,
            sender=ExternalAPISettings,
        )
        post_delete.connect(
            signals.delete_dj_stripe_keys,
            sender=ExternalAPISettings,
        )
