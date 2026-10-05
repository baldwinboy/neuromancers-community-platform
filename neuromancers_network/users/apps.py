from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "neuromancers_network.users"
    verbose_name = _("Users")

    def ready(self):
        """Connect account lifecycle event emitters."""
        from neuromancers_network.users import signals  # noqa: PLC0415

        signals.connect_signals()
