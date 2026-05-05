import re

from django.db import models
from wagtail import blocks
from wagtail.admin.panels import (
    FieldPanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
)
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.fields import RichTextField, StreamField
from wagtail.images import get_image_model_string
from wagtail.models import Page

from .blocks import (
    BackButtonBlock as BackButtonStreamBlock,
    BlogFeedBlock,
    ColorDefinitionBlock,
    CTABlock,
    FAQBlock,
    FeatureGridBlock,
    FontBlock,
    GridBlock,
    HeroBlock,
    MarqueeBlock,
    SpacerBlock,
    StyledRichTextBlock,
    TestimonialBlock,
    TextBlock,
    TextImageBlock,
)


def get_shared_streamfield_blocks():
    """
    Returns the shared StreamField block types used across multiple page types.
    Use this to ensure consistency between HomePage, BlogIndexPage, ContactFormPage, etc.
    """
    return [
        ("hero", HeroBlock()),
        ("text", TextBlock()),
        ("styled_text", StyledRichTextBlock()),
        ("text_image", TextImageBlock()),
        ("cta", CTABlock()),
        ("testimonial", TestimonialBlock()),
        ("features", FeatureGridBlock()),
        ("faq", FAQBlock()),
        ("spacer", SpacerBlock()),
        ("grid", GridBlock()),
        ("marquee", MarqueeBlock()),
        ("blog_feed", BlogFeedBlock()),
        ("back_button", BackButtonStreamBlock()),
    ]


class HomePage(Page):
    max_count = 1

    body = StreamField(
        get_shared_streamfield_blocks(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Build your page by adding blocks",
    )

    subpage_types = [
        "events.SessionsIndexPage",
        "contact.ContactFormPage",
        "blog.BlogIndexPage",
    ]

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]


class StandardPage(Page):
    body = StreamField(
        get_shared_streamfield_blocks(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Build your page by adding blocks",
    )

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    parent_page_types = [
        "core.HomePage",
        "blog.BlogIndexPage",
        "events.SessionsIndexPage",
    ]
    subpage_types = [
        "core.StandardPage",
        "blog.BlogIndexPage",
        "events.SessionsIndexPage",
    ]


@register_setting(icon="link")
class Links(BaseGenericSetting):
    terms_and_conditions = models.URLField(
        help_text="Your organisation's terms and conditions URL"
    )


@register_setting(icon="mail")
class EmailTemplateSettings(BaseGenericSetting):
    """
    Customizable text content for notification emails.

    Each email type has a greeting, main message, and closing message
    that can be customized by admins without editing templates.
    """

    # Account Created Email
    account_created_greeting = RichTextField(
        default="Your account has been created successfully. Welcome to our community!",
        help_text="Greeting text for account creation notification",
    )
    account_created_body = RichTextField(
        default="Start by exploring sessions, connecting with peers, or setting up your profile. If you have any questions, our support team is here to help.",
        help_text="Main body text for account creation notification",
    )

    # Account Closed Email
    account_closed_greeting = RichTextField(
        default="We're sorry to see you go. Your account has been closed as requested.",
        help_text="Greeting text for account closure notification",
    )
    account_closed_body = RichTextField(
        default="If you have any questions about your account closure or need to retrieve any information, please contact our support team within 30 days of this notice.",
        help_text="Main body text for account closure notification",
    )
    account_closed_note = RichTextField(
        default="We hope to see you in the community again someday!",
        help_text="Closing note for account closure notification",
    )

    # Group Status Changed Email
    group_upgrade_greeting = RichTextField(
        default="Congratulations! You've been upgraded to a Peer in the Neuromancers community.",
        help_text="Greeting text when user is upgraded to Peer",
    )
    group_upgrade_body = RichTextField(
        default="As a Peer, you can now create sessions and share your expertise with support seekers. Complete your profile and set up your session offerings to get started.",
        help_text="Main body text for Peer upgrade notification",
    )
    group_downgrade_greeting = RichTextField(
        default="Your account role has been updated.",
        help_text="Greeting text when user role changes (general)",
    )
    group_downgrade_body = RichTextField(
        default="Your role has been updated in our community. Please review your account settings to see what features are available to you.",
        help_text="Main body text for general role change notification",
    )

    # Session Published Email
    session_published_greeting = RichTextField(
        default="Congratulations! Your session has been published.",
        help_text="Greeting text for session published notification (shown to host)",
    )
    session_published_body = RichTextField(
        default="Your session is now visible to support seekers. Support seekers can now request sessions with you. Check your notifications regularly for new requests.",
        help_text="Main body text for session published notification",
    )

    # Session Requested Email
    session_requested_greeting = RichTextField(
        default="A support seeker has requested to book your session.",
        help_text="Greeting text for session request notification (shown to host)",
    )
    session_requested_body = RichTextField(
        default="Review this request and either approve or decline it.",
        help_text="Main body text for session request notification",
    )

    # Session Approved Email
    session_approved_greeting = RichTextField(
        default="Great news! Your request has been approved.",
        help_text="Greeting text for session approval notification (shown to seeker)",
    )
    session_approved_body = RichTextField(
        default="Your session is now confirmed. Please arrive a few minutes early. If you have any questions, reach out to your host.",
        help_text="Main body text for session approval notification",
    )

    # Payment Made Email
    payment_made_greeting = RichTextField(
        default="Thank you for your payment! Your session is now confirmed.",
        help_text="Greeting text for payment confirmation (shown to seeker)",
    )
    payment_made_body = RichTextField(
        default="Your payment has been securely processed through Stripe. You'll receive a separate confirmation email from Stripe with your receipt.",
        help_text="Main body text for payment confirmation",
    )

    # Payment Received Email
    payment_received_greeting = RichTextField(
        default="You've received a payment for your session!",
        help_text="Greeting text for payment received notification (shown to host)",
    )
    payment_received_body = RichTextField(
        default="The payment has been processed and transferred to your connected Stripe account. You can view your payment history and balance in your account dashboard.",
        help_text="Main body text for payment received notification",
    )

    # Refund Requested Email
    refund_requested_greeting = RichTextField(
        default="A support seeker has requested a refund for their session payment.",
        help_text="Greeting text for refund request notification (shown to host)",
    )
    refund_requested_body = RichTextField(
        default="Please review this request and decide whether to approve or decline the refund. You can manage this in your account.",
        help_text="Main body text for refund request notification",
    )
    refund_requested_note = RichTextField(
        default="Note: You're not required to approve this refund, but doing so helps maintain a positive experience for support seekers.",
        help_text="Note text shown at end of refund request notification",
    )

    # Refund Approved Email
    refund_approved_greeting = RichTextField(
        default="Good news! Your refund request has been approved.",
        help_text="Greeting text for refund approval notification (shown to seeker)",
    )
    refund_approved_body = RichTextField(
        default="We appreciate your understanding. If you have any feedback about your experience, we'd love to hear from you.",
        help_text="Main body text for refund approval notification",
    )

    panels = [
        TabbedInterface(
            [
                ObjectList(
                    [
                        FieldPanel("account_created_greeting"),
                        FieldPanel("account_created_body"),
                    ],
                    heading="Account Created",
                ),
                ObjectList(
                    [
                        FieldPanel("account_closed_greeting"),
                        FieldPanel("account_closed_body"),
                        FieldPanel("account_closed_note"),
                    ],
                    heading="Account Closed",
                ),
                ObjectList(
                    [
                        FieldPanel("group_upgrade_greeting"),
                        FieldPanel("group_upgrade_body"),
                        FieldPanel("group_downgrade_greeting"),
                        FieldPanel("group_downgrade_body"),
                    ],
                    heading="Group Status Changed",
                ),
                ObjectList(
                    [
                        FieldPanel("session_published_greeting"),
                        FieldPanel("session_published_body"),
                    ],
                    heading="Session Published",
                ),
                ObjectList(
                    [
                        FieldPanel("session_requested_greeting"),
                        FieldPanel("session_requested_body"),
                    ],
                    heading="Session Requested",
                ),
                ObjectList(
                    [
                        FieldPanel("session_approved_greeting"),
                        FieldPanel("session_approved_body"),
                    ],
                    heading="Session Approved",
                ),
                ObjectList(
                    [
                        FieldPanel("payment_made_greeting"),
                        FieldPanel("payment_made_body"),
                    ],
                    heading="Payment Made",
                ),
                ObjectList(
                    [
                        FieldPanel("payment_received_greeting"),
                        FieldPanel("payment_received_body"),
                    ],
                    heading="Payment Received",
                ),
                ObjectList(
                    [
                        FieldPanel("refund_requested_greeting"),
                        FieldPanel("refund_requested_body"),
                        FieldPanel("refund_requested_note"),
                    ],
                    heading="Refund Requested",
                ),
                ObjectList(
                    [
                        FieldPanel("refund_approved_greeting"),
                        FieldPanel("refund_approved_body"),
                    ],
                    heading="Refund Approved",
                ),
            ]
        )
    ]

    class Meta:
        verbose_name = "Email Templates"


@register_setting(icon="view")
class WebDesignSettings(BaseGenericSetting):
    """
    Customizable settings for web design elements like colors, fonts, and logos.

    Organized into tabs:
    - Fonts: Custom font definitions and root font assignments
    - Colors: Custom color palette and root color customization
    - Branding: Logo and favicon
    - Pages: Programmatic page styling
    - Back Button: Global back button configuration
    - Links: Link hover state styling
    """

    # Custom fonts (uploaded via link)
    custom_fonts = StreamField(
        [("font", FontBlock())],
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Add custom fonts using CSS links from services like fonts.bunny.net or Google Fonts",
    )

    # Root font assignments
    heading_font = models.CharField(
        max_length=100,
        default='"Handjet", monospace',
        help_text='Font family for headings, e.g. "Handjet", monospace',
    )
    subheading_font = models.CharField(
        max_length=100,
        default='"Roboto", sans-serif',
        help_text='Font family for subheadings, e.g. "Roboto", sans-serif',
    )
    body_font = models.CharField(
        max_length=100,
        default='"Open Dyslexic", sans-serif',
        help_text='Font family for body text, e.g. "Open Dyslexic", sans-serif',
    )

    # Core colors
    color_white = models.CharField(
        max_length=50,
        default="hsl(0, 0%, 100%)",
        help_text="White color value (HSL or HEX)",
    )
    color_black = models.CharField(
        max_length=50,
        default="hsl(0, 100%, 0.78%)",
        help_text="Black color value (HSL or HEX)",
    )

    # Safe accent colors (WCAG compliant)
    color_safe_light_accent = models.CharField(
        max_length=50,
        default="hsl(342.63, 80.85%, 81.57%)",
        verbose_name="Safe Light Accent",
        help_text="Light accent color that passes WCAG contrast",
    )
    color_safe_dark_accent = models.CharField(
        max_length=50,
        default="hsl(0, 0%, 0%)",
        verbose_name="Safe Dark Accent",
        help_text="Dark accent color that passes WCAG contrast",
    )
    color_safe_inverse_accent = models.CharField(
        max_length=50,
        default="hsl(0, 0%, 0%)",
        verbose_name="Safe Inverse Accent",
        help_text="Inverse accent color that passes WCAG contrast",
    )
    color_safe_inverse_light_accent = models.CharField(
        max_length=50,
        default="hsl(0, 0%, 0%)",
        verbose_name="Safe Inverse Light Accent",
        help_text="Inverse light accent that passes WCAG contrast",
    )
    color_safe_inverse_dark_accent = models.CharField(
        max_length=50,
        default="hsl(0, 0%, 100%)",
        verbose_name="Safe Inverse Dark Accent",
        help_text="Inverse dark accent that passes WCAG contrast",
    )

    # Brand accent colors
    color_accent = models.CharField(
        max_length=50,
        default="hsl(342.63, 80.85%, 81.57%)",
        verbose_name="Accent",
        help_text="Primary brand accent color",
    )
    color_light_accent = models.CharField(
        max_length=50,
        default="hsl(343.29, 95.89%, 71.37%)",
        verbose_name="Light Accent",
        help_text="Lighter variant of brand accent",
    )
    color_dark_accent = models.CharField(
        max_length=50,
        default="hsl(342.11, 40.43%, 27.65%)",
        verbose_name="Dark Accent",
        help_text="Darker variant of brand accent",
    )

    # Custom colors
    custom_colors = StreamField(
        [("color", ColorDefinitionBlock())],
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Define additional custom colors for the color picker",
    )

    # BRANDING TAB
    logo = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Site logo (recommended: SVG or PNG with transparency)",
    )
    logo_alt_text = models.CharField(
        max_length=100,
        default="Site logo",
        help_text="Alt text for the logo image",
    )
    favicon = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Favicon (recommended: 32x32 or 64x64 PNG)",
    )

    # PROGRAMMATIC PAGES TAB
    # programmatic_page_styles = StreamField(
    #     [("page_style", ProgrammaticPageStyleBlock())],
    #     blank=True,
    #     null=True,
    #     use_json_field=True,
    #     help_text="Customize labels, buttons, and colors for programmatic (non-Wagtail) pages",
    # )

    # BACK BUTTON TAB
    # show_back_button = models.BooleanField(
    #     default=True,
    #     help_text="Show back button on all pages",
    # )
    # back_button_text = models.CharField(
    #     max_length=100,
    #     default="Back",
    #     help_text="Default back button text",
    # )
    # back_button_position = models.CharField(
    #     max_length=20,
    #     choices=[
    #         ("top-left", "Top Left"),
    #         ("top-right", "Top Right"),
    #         ("top-center", "Top Center"),
    #     ],
    #     default="top-left",
    #     help_text="Back button position",
    # )
    # back_button_font = models.CharField(
    #     max_length=100,
    #     blank=True,
    #     help_text="Font family for back button (leave blank for body font)",
    # )
    # back_button_text_color = models.CharField(
    #     max_length=50,
    #     blank=True,
    #     help_text="Back button text color",
    # )
    # back_button_background_color = models.CharField(
    #     max_length=50,
    #     blank=True,
    #     help_text="Back button background color",
    # )
    # back_button_show_icon = models.BooleanField(
    #     default=True,
    #     help_text="Show arrow icon on back button",
    # )

    # PANELS & TABBED INTERFACE
    fonts_panels = [
        FieldPanel("custom_fonts"),
        MultiFieldPanel(
            [
                FieldPanel("heading_font"),
                FieldPanel("subheading_font"),
                FieldPanel("body_font"),
            ],
            heading="Root Font Assignments",
        ),
    ]

    colors_panels = [
        MultiFieldPanel(
            [
                FieldPanel("color_white"),
                FieldPanel("color_black"),
            ],
            heading="Base Colors",
        ),
        MultiFieldPanel(
            [
                FieldPanel("color_safe_light_accent"),
                FieldPanel("color_safe_dark_accent"),
                FieldPanel("color_safe_inverse_accent"),
                FieldPanel("color_safe_inverse_light_accent"),
                FieldPanel("color_safe_inverse_dark_accent"),
            ],
            heading="Safe Accent Colors (WCAG Compliant)",
        ),
        MultiFieldPanel(
            [
                FieldPanel("color_accent"),
                FieldPanel("color_light_accent"),
                FieldPanel("color_dark_accent"),
            ],
            heading="Brand Accent Colors",
        ),
        FieldPanel("custom_colors"),
    ]

    branding_panels = [
        FieldPanel("logo"),
        FieldPanel("logo_alt_text"),
        FieldPanel("favicon"),
    ]

    # pages_panels = [
    #     FieldPanel("programmatic_page_styles"),
    # ]

    edit_handler = TabbedInterface(
        [
            ObjectList(fonts_panels, heading="Fonts"),
            ObjectList(colors_panels, heading="Colors"),
            ObjectList(branding_panels, heading="Branding"),
            # ObjectList(pages_panels, heading="Pages"),
        ]
    )

    def get_color_choices(self):
        """
        Returns the list of color choices for the color picker widget.
        Includes both default colors and custom colors.
        """
        choices = [
            ("transparent", "Transparent"),
            ("white", "White"),
            ("black", "Black"),
            ("safeLightAccent", "Safe Light Accent"),
            ("safeDarkAccent", "Safe Dark Accent"),
            ("safeInverseAccent", "Safe Inverse Accent"),
            ("safeInverseLightAccent", "Safe Inverse Light Accent"),
            ("safeInverseDarkAccent", "Safe Inverse Dark Accent"),
            ("accent", "Accent"),
            ("lightAccent", "Light Accent"),
            ("darkAccent", "Dark Accent"),
        ]

        # Add custom colors
        if self.custom_colors:
            for block in self.custom_colors:
                if block.block_type == "color":
                    choices.append((block.value["name"], block.value["label"]))

        return choices

    def get_color_map(self):
        """
        Returns a dictionary mapping color names to their values.
        """
        color_map = {
            "transparent": "transparent",
            "white": self.color_white,
            "black": self.color_black,
            "safeLightAccent": self.color_safe_light_accent,
            "safeDarkAccent": self.color_safe_dark_accent,
            "safeInverseAccent": self.color_safe_inverse_accent,
            "safeInverseLightAccent": self.color_safe_inverse_light_accent,
            "safeInverseDarkAccent": self.color_safe_inverse_dark_accent,
            "accent": self.color_accent,
            "lightAccent": self.color_light_accent,
            "darkAccent": self.color_dark_accent,
        }

        # Add custom colors
        if self.custom_colors:
            for block in self.custom_colors:
                if block.block_type == "color":
                    color_map[block.value["name"]] = block.value["value"]

        return color_map

    def get_font_choices(self):
        """
        Returns the list of font choices including default and custom fonts.
        """
        choices = [
            ("heading", f"Heading ({self.heading_font})"),
            ("subheading", f"Subheading ({self.subheading_font})"),
            ("body", f"Body ({self.body_font})"),
        ]

        if self.custom_fonts:
            for block in self.custom_fonts:
                if block.block_type == "font":
                    choices.append(
                        (
                            block.value["font_family"],
                            block.value["label"],
                        )
                    )

        return choices

    def get_font_list(self):
        """
        Returns a list of font values for the font picker widget, including both root fonts and custom fonts.
        """
        heading_font_label = re.search(r'["\']([^"\']+)["\']', self.heading_font).group(
            1
        )
        heading_font_label = f"Heading ({heading_font_label})"
        subheading_font_label = re.search(
            r'["\']([^"\']+)["\']', self.subheading_font
        ).group(1)
        subheading_font_label = f"Subheading ({subheading_font_label})"
        body_font_label = re.search(r'["\']([^"\']+)["\']', self.body_font).group(1)
        body_font_label = f"Body ({body_font_label})"
        font_list = [
            (heading_font_label, self.heading_font),
            (subheading_font_label, self.subheading_font),
            (body_font_label, self.body_font),
        ]

        if self.custom_fonts:
            for block in self.custom_fonts:
                if block.block_type == "font":
                    font_list.append((block.value["label"], block.value["font_family"]))

        return font_list

    def get_font_json_list(self):
        """
        Returns a JSON-serializable list of font choices for use in the font picker widget.
        """
        font_list = self.get_font_list()
        return [
            {
                "type": f"FONT_FAMILY_{label.upper().replace(' ', '_')}",
                "label": label,
                "description": label,
                "style": {"fontFamily": value},
                "value": value,
            }
            for label, value in font_list
        ]

    def get_font_links(self):
        """
        Returns a list of font link URLs for inclusion in the page header.
        Extracts URLs from custom font blocks.
        """
        links = []
        if self.custom_fonts:
            for block in self.custom_fonts:
                if block.block_type == "font":
                    url = block.value["link"]
                    if url:
                        links.append(url)
        return links

    class Meta:
        verbose_name = "Web Design"


# ---------------------------------------------------------------------------
# Navigation Settings
# ---------------------------------------------------------------------------

class ExtraLinkBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, help_text="Link text")
    url = blocks.URLBlock(required=True, help_text="Link URL")
    open_in_new_tab = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Open this link in a new browser tab",
    )

    class Meta:
        icon = "link"
        label = "Extra Link"


@register_setting(icon="list-ul")
class NavigationSettings(BaseGenericSetting):
    show_profile_button = models.BooleanField(
        default=True,
        help_text="Show the profile button in the header (dropdown with Profile, Settings, Dashboard)",
    )
    show_notifications_button = models.BooleanField(
        default=True,
        help_text="Show the notifications bell in the header",
    )
    logo_text = models.CharField(
        max_length=100,
        default="Sessions",
        help_text="Text displayed next to the logo in the header",
    )
    extra_links = StreamField(
        [("link", ExtraLinkBlock())],
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Additional links to display in the header navigation",
    )

    panels = [
        FieldPanel("logo_text"),
        FieldPanel("show_profile_button"),
        FieldPanel("show_notifications_button"),
        FieldPanel("extra_links"),
    ]

    class Meta:
        verbose_name = "Navigation"


# ---------------------------------------------------------------------------
# Page Content Settings — editable labels for non-Wagtail (programmatic) pages
# ---------------------------------------------------------------------------

@register_setting(icon="doc-full")
class ProfilePageContent(BaseGenericSetting):
    about_heading = models.CharField(max_length=100, default="About me")
    hosting_heading = models.CharField(max_length=100, default="Hosting")
    attending_heading = models.CharField(max_length=100, default="Attending")
    no_sessions_text = models.CharField(
        max_length=200,
        default="No sessions available.",
    )
    badge_text = models.CharField(max_length=100, default="Trained with Neuromancers")
    dashboard_button_label = models.CharField(max_length=50, default="Dashboard")
    settings_button_label = models.CharField(max_length=50, default="Settings")
    create_session_button_label = models.CharField(
        max_length=50, default="Create Session"
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("about_heading"),
                FieldPanel("hosting_heading"),
                FieldPanel("attending_heading"),
                FieldPanel("no_sessions_text"),
            ],
            heading="Section Headings",
        ),
        MultiFieldPanel(
            [
                FieldPanel("badge_text"),
            ],
            heading="Badge",
        ),
        MultiFieldPanel(
            [
                FieldPanel("dashboard_button_label"),
                FieldPanel("settings_button_label"),
                FieldPanel("create_session_button_label"),
            ],
            heading="Button Labels",
        ),
    ]

    class Meta:
        verbose_name = "Page Content: Profile"


@register_setting(icon="doc-full")
class DashboardPageContent(BaseGenericSetting):
    page_title = models.CharField(max_length=100, default="Host Dashboard")
    page_subtitle = models.CharField(
        max_length=200,
        default="Manage your session requests, approvals, and refunds.",
    )
    peer_tab_label = models.CharField(max_length=50, default="Peer Requests")
    group_tab_label = models.CharField(max_length=50, default="Group Requests")
    refunds_tab_label = models.CharField(max_length=50, default="Refunds")
    empty_peer_text = models.CharField(
        max_length=200, default="No peer requests yet."
    )
    empty_group_text = models.CharField(
        max_length=200, default="No group requests yet."
    )
    empty_refund_text = models.CharField(
        max_length=200, default="No refund requests yet."
    )
    back_to_profile_label = models.CharField(max_length=50, default="Back to Profile")

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("page_title"),
                FieldPanel("page_subtitle"),
                FieldPanel("back_to_profile_label"),
            ],
            heading="Page Header",
        ),
        MultiFieldPanel(
            [
                FieldPanel("peer_tab_label"),
                FieldPanel("group_tab_label"),
                FieldPanel("refunds_tab_label"),
            ],
            heading="Tab Labels",
        ),
        MultiFieldPanel(
            [
                FieldPanel("empty_peer_text"),
                FieldPanel("empty_group_text"),
                FieldPanel("empty_refund_text"),
            ],
            heading="Empty States",
        ),
    ]

    class Meta:
        verbose_name = "Page Content: Dashboard"


@register_setting(icon="doc-full")
class NotificationsPageContent(BaseGenericSetting):
    page_title = models.CharField(max_length=100, default="Notifications")
    mark_all_read_label = models.CharField(max_length=50, default="Mark all read")
    clear_label = models.CharField(max_length=50, default="Clear read")
    empty_text = models.CharField(
        max_length=200, default="You don't have any notifications yet."
    )

    panels = [
        FieldPanel("page_title"),
        FieldPanel("mark_all_read_label"),
        FieldPanel("clear_label"),
        FieldPanel("empty_text"),
    ]

    class Meta:
        verbose_name = "Page Content: Notifications"


@register_setting(icon="doc-full")
class SessionDetailPageContent(BaseGenericSetting):
    back_to_sessions_label = models.CharField(
        max_length=50, default="Back to sessions"
    )
    peer_session_label = models.CharField(max_length=50, default="Peer Session")
    group_session_label = models.CharField(max_length=50, default="Group Session")
    hosted_by_label = models.CharField(max_length=50, default="Hosted by")
    about_section_title = models.CharField(
        max_length=100, default="About this session"
    )
    add_to_calendar_label = models.CharField(max_length=50, default="Add to Calendar")

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("back_to_sessions_label"),
                FieldPanel("about_section_title"),
                FieldPanel("add_to_calendar_label"),
            ],
            heading="Labels",
        ),
        MultiFieldPanel(
            [
                FieldPanel("peer_session_label"),
                FieldPanel("group_session_label"),
                FieldPanel("hosted_by_label"),
            ],
            heading="Session Type Labels",
        ),
    ]

    class Meta:
        verbose_name = "Page Content: Session Detail"
