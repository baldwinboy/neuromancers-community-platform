from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting
from wagtail.contrib.settings.models import register_setting

from neuromancers_network.core.panels import StripePriceChooserPanel


@register_setting(icon="cog")
class PeerRequirementsSettings(BaseGenericSetting):
    """Admin-controlled requirements a user must meet to act as a peer."""

    require_subscription = models.BooleanField(
        _("Require an active subscription"),
        default=True,
    )
    require_kyc = models.BooleanField(
        _("Require completed Stripe KYC"),
        default=True,
    )
    require_verification_to_publish = models.BooleanField(
        _("Require moderator verification to publish"),
        default=False,
    )
    peer_plan_price_ids = models.JSONField(
        _("Peer plan Stripe Price IDs"),
        default=list,
        blank=True,
        help_text=_("Stripe Price IDs that grant peer access."),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("require_subscription"),
                FieldPanel("require_kyc"),
                FieldPanel("require_verification_to_publish"),
                StripePriceChooserPanel("peer_plan_price_ids"),
            ],
            heading=_("Peer requirements"),
        ),
    ]

    class Meta:
        verbose_name = _("Peer Requirements Settings")
