from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting
from wagtail.contrib.settings.models import register_setting

from neuromancers_network.core.fields import EncryptedCharField
from neuromancers_network.core.panels import SendTestEmailPanel
from neuromancers_network.core.panels import StripeOpsPanel


def language_choices():
    """Code-level supported languages (the superset the admin may offer)."""
    return list(getattr(settings, "LANGUAGES", [("en", "English")]))


@register_setting(icon="cogs")
class StripeSettings(BaseGenericSetting):
    """Runtime Stripe configuration editable by Wagtail admins."""

    class ChargeType(models.TextChoices):
        DIRECT = "direct", _("Direct charges (peer is merchant of record)")
        DESTINATION = "destination", _("Destination charges")

    class TaxMode(models.TextChoices):
        STRIPE_TAX = "stripe_tax", _("Stripe Tax")
        OFF = "off", _("Off")

    publishable_key = models.CharField(
        _("Publishable key"),
        max_length=255,
        blank=True,
    )
    secret_key = EncryptedCharField(
        _("Secret key"),
        max_length=255,
        blank=True,
    )
    webhook_secret = EncryptedCharField(
        _("Webhook secret"),
        max_length=255,
        blank=True,
    )
    client_id = EncryptedCharField(
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
    charge_type = models.CharField(
        _("Charge type"),
        max_length=20,
        choices=ChargeType.choices,
        default=ChargeType.DIRECT,
        help_text=_(
            "How meeting payments are charged. Direct makes the care provider "
            "the merchant of record; destination routes funds via a transfer.",
        ),
    )
    connect_country = models.CharField(
        _("Connect country"),
        max_length=2,
        default="GB",
        help_text=_("Two-letter country code for new Express connected accounts."),
    )
    tax_mode = models.CharField(
        _("Tax mode"),
        max_length=20,
        choices=TaxMode.choices,
        default=TaxMode.STRIPE_TAX,
        help_text=_("Automatic tax collection on checkout sessions."),
    )
    allow_partial_refunds = models.BooleanField(
        _("Allow partial refunds"),
        default=False,
        help_text=_("Let peers and admins refund part of a payment."),
    )
    subscription_enabled = models.BooleanField(
        _("Subscriptions enabled"),
        default=True,
        help_text=_("Show the peer subscribe button."),
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
                FieldPanel("charge_type"),
                FieldPanel("connect_country"),
                FieldPanel("client_id"),
                FieldPanel("application_fee"),
                FieldPanel("onboarding_redirect_url"),
                FieldPanel("onboarding_refresh_url"),
            ],
            heading=_("Connect"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("tax_mode"),
                FieldPanel("allow_partial_refunds"),
                FieldPanel("subscription_enabled"),
            ],
            heading=_("Compliance"),
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
    password = EncryptedCharField(_("Password"), max_length=255, blank=True)
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

    class MeetingProvider(models.TextChoices):
        WHEREBY = "whereby", _("Whereby")
        DAILY = "daily", _("Daily.co")

    meeting_provider = models.CharField(
        _("Meeting provider"),
        max_length=20,
        choices=MeetingProvider.choices,
        default=MeetingProvider.WHEREBY,
        help_text=_("Service used to generate meeting links for bookings."),
    )
    meeting_room_prefix = models.CharField(
        _("Meeting room prefix"),
        max_length=50,
        default="neuromancers",
        help_text=_("Prefix for generated meeting room names."),
    )
    joining_lead_minutes = models.PositiveSmallIntegerField(
        _("Join window lead (minutes)"),
        default=10,
        help_text=_("How long before a session starts the join link opens."),
    )
    getpronto_api_key = EncryptedCharField(
        _("GetPronto API Key"),
        max_length=255,
        blank=True,
        help_text=_("API key for GetPronto integration."),
    )
    whereby_api_key = EncryptedCharField(
        _("Whereby API Key"),
        max_length=255,
        blank=True,
        help_text=_("API key for Whereby integration."),
    )
    daily_api_key = EncryptedCharField(
        _("Daily API Key"),
        max_length=255,
        blank=True,
        help_text=_("API key for Daily.co integration."),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("meeting_provider"),
                FieldPanel("meeting_room_prefix"),
                FieldPanel("joining_lead_minutes"),
            ],
            heading=_("Meeting rooms"),
        ),
        MultiFieldPanel(
            [FieldPanel("getpronto_api_key")],
            heading=_("GetPronto"),
        ),
        MultiFieldPanel(
            [FieldPanel("whereby_api_key")],
            heading=_("Whereby"),
        ),
        MultiFieldPanel(
            [FieldPanel("daily_api_key")],
            heading=_("Daily.co"),
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


@register_setting(icon="user")
class AccountSettings(BaseGenericSetting):
    """Admin-controlled cooldowns for member identity changes."""

    username_change_cooldown_days = models.PositiveIntegerField(
        _("Username change cooldown (days)"),
        default=30,
        help_text=_(
            "Days a member must wait between username changes. Zero disables it.",
        ),
    )
    email_change_cooldown_days = models.PositiveIntegerField(
        _("Email change cooldown (days)"),
        default=30,
        help_text=_(
            "Days a member must wait between email changes. Zero disables it.",
        ),
    )
    account_deletion_grace_days = models.PositiveIntegerField(
        _("Account deletion grace period (days)"),
        default=14,
        help_text=_(
            "Days a member has to cancel a deletion request before it is purged.",
        ),
    )
    reregistration_cooldown_days = models.PositiveIntegerField(
        _("Re-registration cooldown (days)"),
        default=180,
        help_text=_(
            "Days a deleted member's email/username stay blocked from re-use.",
        ),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("username_change_cooldown_days"),
                FieldPanel("email_change_cooldown_days"),
            ],
            heading=_("Identity change cooldowns"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("account_deletion_grace_days"),
                FieldPanel("reregistration_cooldown_days"),
            ],
            heading=_("Account deletion"),
        ),
    ]

    class Meta:
        verbose_name = _("Account Settings")
