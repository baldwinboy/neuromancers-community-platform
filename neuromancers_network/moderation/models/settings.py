from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting
from wagtail.contrib.settings.models import register_setting


@register_setting(icon="warning")
class BanSettings(BaseGenericSetting):
    """Admin controls for ban enforcement and retention."""

    ip_enforcement_enabled = models.BooleanField(
        _("Enforce IP bans"),
        default=False,
        help_text=_(
            "Block requests from banned IPs. Keep off until trusted proxies are "
            "configured (RATELIMIT_TRUSTED_PROXIES); while off, IP bans only "
            "record and log.",
        ),
    )
    ip_ban_retention_days = models.PositiveIntegerField(
        _("IP ban retention (days)"),
        default=730,
        help_text=_("How long expired IP ban records are kept before purging."),
    )
    audit_retention_days = models.PositiveIntegerField(
        _("Audit retention (days)"),
        default=730,
        help_text=_("How long account audit entries are kept before purging."),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("ip_enforcement_enabled"),
                FieldPanel("ip_ban_retention_days"),
                FieldPanel("audit_retention_days"),
            ],
            heading=_("Ban enforcement"),
        ),
    ]

    class Meta:
        verbose_name = _("Ban Settings")
