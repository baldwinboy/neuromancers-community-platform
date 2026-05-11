from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting
from wagtail.contrib.settings.models import register_setting
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import PreviewableMixin
from wagtail_link_block.blocks import LinkBlock

from neuromancers_network.common.blocks import AllAuthDesignStreamBlock
from neuromancers_network.common.blocks import AllAuthFormStreamBlock
from neuromancers_network.common.blocks import BackgroundStreamBlock
from neuromancers_network.common.blocks import ColorSchemesStreamBlock
from neuromancers_network.common.blocks import ContentBlock
from neuromancers_network.common.blocks import NavbarDesignStreamBlock
from neuromancers_network.common.blocks import ThemesStreamBlock
from neuromancers_network.common.blocks import TypographyStreamBlock


class NavbarPositions(models.TextChoices):
    NORMAL = "normal", _("Normal (stays at the top of page before scrolling)")
    STICKY = "sticky", _("Sticky (stays at the top of the page even when scrolling)")


class KitchensinkPreviewMixin(PreviewableMixin):
    """Mixin to provide a common preview template for settings that don't have
    their own dedicated preview page."""

    def get_preview_template(self, request, mode_name):
        return "core/kitchensink.html"


@register_setting(icon="palette")
class SiteDesignSettings(BaseGenericSetting, KitchensinkPreviewMixin):
    """
    Site-wide design settings, including colour palettes and backgrounds. These
    can be overridden on a per-page basis.
    """

    color_palette = StreamField(
        ColorSchemesStreamBlock(),
    )

    typography = StreamField(
        TypographyStreamBlock(),
    )

    backgrounds = StreamField(
        BackgroundStreamBlock(),
    )
    logo = StreamField(
        [
            ("image", ImageChooserBlock()),
        ],
        block_counts={
            "image": {"max_num": 1},
        },
    )
    panels = [
        FieldPanel("color_palette"),
        FieldPanel("typography"),
        FieldPanel("backgrounds"),
        FieldPanel("logo"),
    ]

    class Meta:
        verbose_name = _("Site Design")


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
    ]

    class Meta:
        verbose_name = _("Email Settings")

    @property
    def is_active(self) -> bool:
        """Only use the stored backend if all required fields are filled."""
        return all([self.host, self.port, self.username, self.password])


@register_setting(icon="lock")
class SiteLockSettings(BaseGenericSetting):
    """Settings for site lock mode (public/private + optional password gate)."""

    is_public = models.BooleanField(
        _("Site is Public"),
        default=True,
        help_text=_(
            "If disabled, visitors are redirected to a lock screen unless unlocked.",
        ),
    )
    password_hash = models.CharField(
        _("Password Hash"),
        max_length=128,
        blank=True,
        help_text=_(
            "Optional hashed password. If empty, middleware fallback password applies.",
        ),
    )
    maintenance_message = models.CharField(
        _("Maintenance Message"),
        max_length=255,
        blank=True,
        help_text=_("Message displayed on the lock screen."),
    )

    panels = [
        FieldPanel("is_public"),
        FieldPanel("password_hash"),
        FieldPanel("maintenance_message"),
    ]

    class Meta:
        verbose_name = _("Site Lock Settings")

    @property
    def is_password_protected(self) -> bool:
        return bool(self.password_hash)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)


@register_setting(icon="pilcrow")
class ContentSettings(BaseGenericSetting, KitchensinkPreviewMixin):
    """
    Settings for default themes, site-wide terminology and AllAuth form content.
    """

    default_theme = StreamField(
        ThemesStreamBlock(),
    )
    default_alert_theme = StreamField(
        ThemesStreamBlock(),
    )
    host_label = models.CharField(
        _("Host Label"),
        max_length=50,
        default="Host",
        help_text=_("Label to use for 'Host' across the site. Default is 'Host'."),
    )
    host_label_plural = models.CharField(
        _("Host Label (Plural)"),
        max_length=50,
        default="Hosts",
        help_text=_(
            "Label to use for plural 'Hosts' across the site. Default is 'Hosts'.",
        ),
    )
    attendee_label = models.CharField(
        _("Attendee Label"),
        max_length=50,
        default="Attendee",
        help_text=_(
            "Label to use for 'Attendee' across the site. Default is 'Attendee'.",
        ),
    )
    attendee_label_plural = models.CharField(
        _("Attendee Label (Plural)"),
        max_length=50,
        default="Attendees",
        help_text=_(
            """
            Label to use for plural 'Attendees' across the site. Default is 'Attendees'.
            """,
        ),
    )
    session_label = models.CharField(
        _("Session Label"),
        max_length=50,
        default="Session",
        help_text=_(
            "Label to use for 'Session' across the site. Default is 'Session'.",
        ),
    )
    session_label_plural = models.CharField(
        _("Session Label (Plural)"),
        max_length=50,
        default="Sessions",
        help_text=_(
            """
            Label to use for plural 'Sessions' across the site.
            Default is 'Sessions'.
            """,
        ),
    )
    peer_label = models.CharField(
        _("Peer Label"),
        max_length=50,
        default="Peer",
        help_text=_("Label to use for 'Peer' across the site. Default is 'Peer'."),
    )
    group_label = models.CharField(
        _("Group Label"),
        max_length=50,
        default="Group",
        help_text=_("Label to use for 'Group' across the site. Default is 'Group'."),
    )
    verified_label = models.CharField(
        _("Verified Label"),
        max_length=50,
        default="Verified",
        help_text=_(
            "Label to indicate verified users across the site. Default is 'Verified'.",
        ),
    )

    # AllAuth form overrides
    allauth_form = StreamField(
        AllAuthFormStreamBlock(),
    )

    panels = [
        FieldPanel("default_theme"),
        FieldPanel("host_label"),
        FieldPanel("host_label_plural"),
        FieldPanel("attendee_label"),
        FieldPanel("attendee_label_plural"),
        FieldPanel("session_label"),
        FieldPanel("session_label_plural"),
        FieldPanel("peer_label"),
        FieldPanel("group_label"),
        FieldPanel("verified_label"),
        FieldPanel("allauth_form"),
    ]

    class Meta:
        verbose_name = _("Content Settings")


@register_setting(icon="cogs")
class ExternalAPISettings(BaseGenericSetting):
    """
    Settings for external API integrations,
    allowing admins to store API keys and endpoints.
    """

    getpronto_api_key = models.CharField(
        _("GetPronto API Key"),
        max_length=255,
        blank=True,
        help_text=_("API key for GetPronto integration."),
    )
    mjml_app_id = models.CharField(
        _("MJML Application ID"),
        max_length=255,
        blank=True,
        help_text=_("Application ID for MJML API integration."),
    )
    mjml_secret_key = models.CharField(
        _("MJML Secret Key"),
        max_length=255,
        blank=True,
        help_text=_(
            "Secret Key for MJML API integration. Use the Secret Key for backend"
            "usage, and the Application ID for frontend usage.",
        ),
    )
    stripe_secret_key = models.CharField(
        _("Stripe Secret Key"),
        max_length=255,
        blank=True,
        help_text=_("Secret key for Stripe integration."),
    )
    stripe_publishable_key = models.CharField(
        _("Stripe Publishable Key"),
        max_length=255,
        blank=True,
        help_text=_("Publishable key for Stripe integration."),
    )
    stripe_client_id = models.CharField(
        _("Stripe Client ID"),
        max_length=255,
        blank=True,
        help_text=_("Client ID for Stripe Connect integration."),
    )
    stripe_onboarding_redirect_url = StreamField(
        [
            (
                "stripe_onboarding_redirect_url",
                LinkBlock(
                    label=_("Stripe Redirect URL"),
                    help_text=_(
                        "The URL to redirect the user to after they leave or complete the onboarding flow.",
                    ),
                ),
            ),
        ],
        max_num=1,
        use_json_field=True,
        collapsed=True,
    )
    stripe_onboarding_refresh_url = StreamField(
        [
            (
                "stripe_onboarding_refresh_url",
                LinkBlock(
                    label=_("Stripe Refresh URL"),
                    help_text=_(
                        "The URL to redirect the user to if the onboarding link expired, was previously visited or is otherwise invalid.",
                    ),
                ),
            ),
        ],
        max_num=1,
        use_json_field=True,
        collapsed=True,
    )
    stripe_application_fee = models.PositiveSmallIntegerField(
        _("Stripe Application Fee (%)"),
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        null=True,
        blank=True,
        help_text=_(
            "The percentage of each payment that you'd like to take from users.",
        ),
        default=15,
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
            [
                FieldPanel("getpronto_api_key"),
            ],
            heading=_("GetPronto Settings"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("mjml_app_id"),
                FieldPanel("mjml_secret_key"),
            ],
            heading=_("MJML Settings"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("stripe_secret_key"),
                FieldPanel("stripe_publishable_key"),
                FieldPanel("stripe_application_fee"),
                MultiFieldPanel(
                    [
                        FieldPanel("stripe_client_id"),
                        FieldPanel("stripe_onboarding_redirect_url"),
                        FieldPanel("stripe_onboarding_refresh_url"),
                    ],
                    heading=_("Stripe Connect Onboarding Settings"),
                ),
            ],
            heading=_("Stripe Settings"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("whereby_api_key"),
                FieldPanel("whereby_room_prefix"),
            ],
            heading=_("Whereby Settings"),
        ),
    ]

    class Meta:
        verbose_name = _("External API Settings")


@register_setting(icon="list-ul")
class NavbarSettings(BaseGenericSetting, KitchensinkPreviewMixin):
    """Admin-controlled navbar appearance."""

    navbar_theme_design = StreamField(
        NavbarDesignStreamBlock(),
    )
    navbar_position = models.CharField(
        max_length=10,
        choices=NavbarPositions.choices,
        default=NavbarPositions.NORMAL,
    )

    panels = [
        FieldPanel("navbar_theme_design"),
        FieldPanel("navbar_position"),
    ]

    class Meta:
        verbose_name = _("Navbar Settings")


@register_setting(icon="collapse-down")
class FooterSettings(BaseGenericSetting, KitchensinkPreviewMixin):
    """Admin-controlled footer. Background is set directly; columns, text,
    and links are built from blocks."""

    content = StreamField(
        ContentBlock(),
    )

    panels = [
        FieldPanel("content"),
    ]

    class Meta:
        verbose_name = _("Footer Settings")


@register_setting(icon="user")
class AllAuthSettings(BaseGenericSetting, KitchensinkPreviewMixin):
    """Per-theme background, fonts, and colors for AllAuth pages (login/signup/etc.)."""

    form_theme_design = StreamField(
        AllAuthDesignStreamBlock(),
    )

    panels = [
        FieldPanel("form_theme_design"),
    ]

    class Meta:
        verbose_name = _("AllAuth Settings")
