from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting
from wagtail.contrib.settings.models import register_setting

from neuromancers_network.core.panels import SendTestEmailPanel
from neuromancers_network.core.panels import StripeOpsPanel


def language_choices():
    """Code-level supported languages (the superset the admin may offer)."""
    return list(getattr(settings, "LANGUAGES", [("en", "English")]))


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
    client_id = models.CharField(
        _("Client ID"),
        max_length=255,
        blank=True,
        help_text=_("Client ID for Stripe Connect integration."),
    )
    application_fee = models.PositiveSmallIntegerField(
        _("Application fee (%)"),
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        null=True,
        blank=True,
        default=15,
        help_text=_(
            "The percentage of each payment that you'd like to take from users.",
        ),
    )
    onboarding_redirect_url = models.URLField(
        _("Onboarding redirect URL"),
        blank=True,
        help_text=_(
            "The URL to redirect the user to after they leave or complete the"
            " Stripe Connect onboarding flow.",
        ),
    )
    onboarding_refresh_url = models.URLField(
        _("Onboarding refresh URL"),
        blank=True,
        help_text=_(
            "The URL to redirect the user to if the Stripe Connect onboarding"
            " link expired, was previously visited or is otherwise invalid.",
        ),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("publishable_key"),
                FieldPanel("secret_key"),
                FieldPanel("webhook_secret"),
            ],
            heading=_("API Keys"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("client_id"),
                FieldPanel("application_fee"),
                FieldPanel("onboarding_redirect_url"),
                FieldPanel("onboarding_refresh_url"),
            ],
            heading=_("Connect"),
        ),
        StripeOpsPanel(),
    ]

    class Meta:
        verbose_name = _("Stripe Settings")

    @property
    def is_ready(self) -> bool:
        """Whether enough Stripe credentials are configured to operate."""
        return bool(self.publishable_key and self.secret_key)


@register_setting(icon="mail")
class EmailSettings(BaseGenericSetting):
    """SMTP configuration editable by Wagtail admins at runtime."""

    host = models.CharField(_("SMTP Host"), max_length=255, blank=True)
    port = models.PositiveIntegerField(_("Port"), default=587)
    username = models.CharField(_("Username"), max_length=255, blank=True)
    password = models.CharField(_("Password"), max_length=255, blank=True)
    use_tls = models.BooleanField(_("Use TLS"), default=True)
    use_ssl = models.BooleanField(_("Use SSL"), default=False)
    default_from_email = models.EmailField(
        _("From Address"),
        blank=True,
        help_text=_(
            """
            Default sender address for outgoing emails.
            Optional, but recommended.
            To include a display name, use the format 'Name <email@example.com>'.""",
        ),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("host"),
                FieldPanel("port"),
                FieldPanel("username"),
                FieldPanel("password"),
                FieldPanel("use_tls"),
                FieldPanel("use_ssl"),
            ],
            heading=_("SMTP Configuration"),
        ),
        FieldPanel("default_from_email"),
        SendTestEmailPanel(),
    ]

    class Meta:
        verbose_name = _("Email Settings")

    @property
    def is_active(self) -> bool:
        """Only use the stored backend if all required fields are filled."""
        return all([self.host, self.port, self.username, self.password])


@register_setting(icon="cogs")
class IntegrationSettings(BaseGenericSetting):
    """API keys for external integrations, editable by Wagtail admins."""

    getpronto_api_key = models.CharField(
        _("GetPronto API Key"),
        max_length=255,
        blank=True,
        help_text=_("API key for GetPronto integration."),
    )
    whereby_api_key = models.CharField(
        _("Whereby API Key"),
        max_length=255,
        blank=True,
        help_text=_("API key for Whereby integration."),
    )
    whereby_room_prefix = models.CharField(
        _("Whereby Room Prefix"),
        max_length=50,
        default="neuromancers",
        help_text=_("Prefix for Whereby room names. Default is 'neuromancers'."),
    )

    panels = [
        MultiFieldPanel(
            [FieldPanel("getpronto_api_key")],
            heading=_("GetPronto"),
        ),
        MultiFieldPanel(
            [FieldPanel("whereby_api_key"), FieldPanel("whereby_room_prefix")],
            heading=_("Whereby"),
        ),
    ]

    class Meta:
        verbose_name = _("Integration Settings")


class LanguageSwitcherStyle(models.TextChoices):
    DROPDOWN = "dropdown", _("Dropdown")
    INLINE = "inline", _("Inline")
    SIDEBAR = "sidebar", _("Sidebar")


class ExchangeRateSource(models.TextChoices):
    STRIPE = "stripe", _("Stripe adaptive pricing")
    MANUAL = "manual", _("Manual rates")
    FIXED = "fixed", _("Fixed rate")


@register_setting(icon="globe")
class LocalizationSettings(BaseGenericSetting):
    """Admin-controlled languages, switcher and display currency."""

    enabled = models.BooleanField(
        _("Enable localization"),
        default=True,
        help_text=_("Offer translations and a language switcher on the site."),
    )
    default_language = models.CharField(
        _("Default language"),
        max_length=10,
        choices=language_choices,
        default="en",
    )
    languages = models.ManyToManyField(
        "taxonomy.Language",
        blank=True,
        related_name="+",
        verbose_name=_("Offered languages"),
        help_text=_("The admin-curated subset of languages offered to visitors."),
    )
    show_language_switcher = models.BooleanField(
        _("Show language switcher"),
        default=True,
    )
    language_switcher_style = models.CharField(
        _("Switcher style"),
        max_length=10,
        choices=LanguageSwitcherStyle,
        default=LanguageSwitcherStyle.DROPDOWN,
    )
    detect_browser_language = models.BooleanField(
        _("Detect browser language"),
        default=True,
        help_text=_("Honour the visitor's Accept-Language header when possible."),
    )
    force_default_language = models.BooleanField(
        _("Force default language"),
        default=False,
        help_text=_("Ignore browser detection and always use the default language."),
    )
    display_currency = models.CharField(
        _("Display currency"),
        max_length=3,
        default="GBP",
        help_text=_("ISO 4217 currency code used when displaying prices."),
    )
    currency_exchange_enabled = models.BooleanField(
        _("Enable currency exchange"),
        default=True,
    )
    exchange_rate_source = models.CharField(
        _("Exchange rate source"),
        max_length=10,
        choices=ExchangeRateSource,
        default=ExchangeRateSource.STRIPE,
    )
    manual_exchange_rates = models.JSONField(
        _("Manual exchange rates"),
        default=dict,
        blank=True,
        help_text=_("Fallback mapping of {currency_code: rate}."),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("enabled"),
                FieldPanel("default_language"),
                FieldPanel("languages"),
            ],
            heading=_("Languages"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_language_switcher"),
                FieldPanel("language_switcher_style"),
                FieldPanel("detect_browser_language"),
                FieldPanel("force_default_language"),
            ],
            heading=_("Switcher"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("display_currency"),
                FieldPanel("currency_exchange_enabled"),
                FieldPanel("exchange_rate_source"),
                FieldPanel("manual_exchange_rates"),
            ],
            heading=_("Currency"),
        ),
    ]

    class Meta:
        verbose_name = _("Localization Settings")


@register_setting(icon="warning")
class ModerationSettings(BaseGenericSetting):
    """Admin-managed username blocklist and moderation rules."""

    username_blocklist = models.TextField(
        _("Username blocklist"),
        blank=True,
        help_text=_("One username per line. Applied at sign up."),
    )
    username_blocklist_use_regex = models.BooleanField(
        _("Treat entries as regular expressions"),
        default=False,
    )
    username_case_sensitive = models.BooleanField(
        _("Case sensitive matching"),
        default=False,
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("username_blocklist"),
                FieldPanel("username_blocklist_use_regex"),
                FieldPanel("username_case_sensitive"),
            ],
            heading=_("Username moderation"),
        ),
    ]

    class Meta:
        verbose_name = _("Moderation Settings")


@register_setting(icon="mail")
class NotificationSettings(BaseGenericSetting):
    """Admin-level notification defaults for the inbox event bus."""

    default_disabled_event_types = models.JSONField(
        _("Default disabled event types"),
        default=list,
        blank=True,
        help_text=_("Event types disabled for members unless they opt back in."),
    )
    transactional_events = models.JSONField(
        _("Transactional event types"),
        default=list,
        blank=True,
        help_text=_("Event types that can never be opted out of."),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("default_disabled_event_types"),
                FieldPanel("transactional_events"),
            ],
            heading=_("Notification defaults"),
        ),
    ]

    class Meta:
        verbose_name = _("Notification Settings")
