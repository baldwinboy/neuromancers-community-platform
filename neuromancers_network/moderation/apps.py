from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ModerationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "neuromancers_network.moderation"
    verbose_name = _("Moderation")
