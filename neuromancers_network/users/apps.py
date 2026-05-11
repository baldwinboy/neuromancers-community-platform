from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "neuromancers_network.users"
    verbose_name = _("Users")

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
        from . import signals  # noqa: PLC0415

        sender = get_user_model()

        post_save.connect(
            signals.create_email_confirmation,
            sender=sender,
        )
