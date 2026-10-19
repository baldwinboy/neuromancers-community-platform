# ruff: noqa: PLC0415
from django.apps import AppConfig
from django.db.models.signals import m2m_changed
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
        from neuromancers_network.core.models import EmailSettings
        from neuromancers_network.core.models import IntegrationSettings
        from neuromancers_network.core.models import LocalizationSettings
        from neuromancers_network.core.models import ModerationSettings
        from neuromancers_network.core.models import NotificationSettings
        from neuromancers_network.core.models import StripeSettings
        from neuromancers_network.users.validators import bust_blocked_usernames_cache

        from . import signals
        from .forms import EmailSettingsForm
        from .forms import IntegrationSettingsForm
        from .forms import LocalizationSettingsForm
        from .forms import NotificationSettingsForm
        from .forms import StripeSettingsForm

        # Set after app loading to avoid a core.models <-> core.forms cycle.
        NotificationSettings.base_form_class = NotificationSettingsForm
        StripeSettings.base_form_class = StripeSettingsForm
        EmailSettings.base_form_class = EmailSettingsForm
        IntegrationSettings.base_form_class = IntegrationSettingsForm
        LocalizationSettings.base_form_class = LocalizationSettingsForm

        post_save.connect(
            signals.update_dj_stripe_keys,
            sender=StripeSettings,
            dispatch_uid="core.signals.update_dj_stripe_keys",
        )
        post_delete.connect(
            signals.delete_dj_stripe_keys,
            sender=StripeSettings,
            dispatch_uid="core.signals.delete_dj_stripe_keys",
        )
        post_save.connect(
            signals.bust_localization_cache,
            sender=LocalizationSettings,
            dispatch_uid="core.signals.bust_localization_settings",
        )
        post_delete.connect(
            signals.bust_localization_cache,
            sender=LocalizationSettings,
            dispatch_uid="core.signals.bust_localization_settings_delete",
        )
        m2m_changed.connect(
            signals.bust_localization_cache,
            sender=LocalizationSettings.languages.through,
            dispatch_uid="core.signals.bust_localization_languages",
        )
        post_save.connect(
            bust_blocked_usernames_cache,
            sender=ModerationSettings,
            dispatch_uid="core.signals.bust_moderation_blocklist",
        )
        post_delete.connect(
            bust_blocked_usernames_cache,
            sender=ModerationSettings,
            dispatch_uid="core.signals.bust_moderation_blocklist_delete",
        )
