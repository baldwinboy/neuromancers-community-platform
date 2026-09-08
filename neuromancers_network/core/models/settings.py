from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting
from wagtail.contrib.settings.models import register_setting


@register_setting(icon="cogs")
class StripeSettings(BaseGenericSetting):
    """Runtime Stripe configuration editable by Wagtail admins."""

    publishable_key = models.CharField(
        _("Publishable key"),
        max_length=255,
        blank=True,
    )
    secret_key = models.CharField(
        _("Secret key"),
        max_length=255,
        blank=True,
    )
    webhook_secret = models.CharField(
        _("Webhook secret"),
        max_length=255,
        blank=True,
    )

    panels = [
        FieldPanel("publishable_key"),
        FieldPanel("secret_key"),
        FieldPanel("webhook_secret"),
    ]

    class Meta:
        verbose_name = _("Stripe Settings")
