from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MessagingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "neuromancers_network.messaging"
    verbose_name = _("Messaging")
