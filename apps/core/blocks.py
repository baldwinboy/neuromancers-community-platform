"""
Reusable StreamField blocks for Wagtail page building.

These blocks provide flexible, composable components for content editors
to build pages without coding, similar to Squarespace/Webflow.
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from .wagtail_widgets import ColorPickerWidget, EmojiPickerWidget

# Default color choices for backward compatibility
COLOR_CHOICES = [
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

BORDER_CHOICES = [
    ("none", "None"),
    ("zigzag", "Zigzag"),
    ("wave", "Wave"),
    ("rounded", "Rounded"),
    ("legoWave", "Lego Wave"),
    ("leftCurve", "Left Curve"),
    ("rightCurve", "Right Curve"),
]

FONT_CHOICES = [
    ("heading", "Heading Font"),
    ("subheading", "Subheading Font"),
    ("body", "Body Font"),
    ("custom", "Custom Font"),
]


# Default color choices - these are fallback values when WebDesignSettings is not configured
DEFAULT_COLOR_CHOICES = [
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

# For backward compatibility
COLOR_CHOICES = DEFAULT_COLOR_CHOICES


class EmojiChooserBlock(blocks.FieldBlock):
    """
    A block for choosing a single emoji using a visual picker.
    Uses the custom EmojiPickerWidget instead of a dropdown.
    """

    def __init__(self, required=True, help_text=None, **kwargs):
        self.field = blocks.CharBlock(
            required=required,
            help_text=help_text,
            max_length=10,  # Emojis can be multi-codepoint
        ).field
        self.field.widget = EmojiPickerWidget()
        super().__init__(**kwargs)

    class Meta:
        icon = "emoji"


class ColorPickerBlock(blocks.FieldBlock):
    """
    A block for picking a color using a visual color picker.
    Uses WebDesignSettings colors as default options with custom color support.
    """

    def __init__(self, required=False, help_text=None, **kwargs):
        self.field = blocks.CharBlock(
            required=required,
            help_text=help_text,
            max_length=50,  # Allow for hex/hsl values
        ).field
        self.field.widget = ColorPickerWidget()
        super().__init__(**kwargs)

    class Meta:
        icon = "colorpicker"


class FontBlock(blocks.StructBlock):
    """
    A block for defining a custom font with link and family name.
    Used in WebDesignSettings to allow admins to add fonts.
    """

    link = blocks.URLBlock(
        required=True,
        help_text="Font CSS URL, e.g. https://fonts.bunny.net/css?family=abeezee:400",
    )
    font_family = blocks.CharBlock(
        required=True,
        max_length=100,
        help_text="CSS font-family value, e.g. 'ABeeZee', sans-serif",
    )
    label = blocks.CharBlock(
        required=True,
        max_length=50,
        help_text="Display label for this font, e.g. ABeeZee",
    )

    class Meta:
        icon = "pilcrow"
        label = "Font"


class ColorDefinitionBlock(blocks.StructBlock):
    """
    A block for defining a custom color with name and value.
    Used in WebDesignSettings to allow admins to add colors.
    """

    name = blocks.CharBlock(
        required=True,
        max_length=50,
        help_text="Color name (camelCase), e.g. customAccent",
    )
    label = blocks.CharBlock(
        required=True,
        max_length=50,
        help_text="Display label, e.g. Custom Accent",
    )
    value = blocks.CharBlock(
        required=True,
        max_length=50,
        help_text="Color value in HSL or HEX, e.g. hsl(342, 80%, 81%) or #FF6B9D",
    )

    class Meta:
        icon = "view"
        label = "Custom Color"


class BackButtonBlock(blocks.StructBlock):
    """
    A block for configuring a back button with customizable styling.
    """

    text = blocks.CharBlock(
        required=True,
        max_length=100,
        default="Back",
        help_text="Button text",
    )
    link = blocks.URLBlock(
        required=False,
        help_text="Custom link URL (leave blank to use browser history)",
    )
    position = blocks.ChoiceBlock(
        choices=[
            ("top-left", "Top Left"),
            ("top-right", "Top Right"),
            ("top-center", "Top Center"),
        ],
        default="top-left",
        help_text="Position of the back button",
    )
    font = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Font family (leave blank for default)",
    )
    text_color = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Text color (color name or hex/hsl value)",
    )
    background_color = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Background color (color name or hex/hsl value)",
    )
    show_icon = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="Show arrow icon",
    )

    class Meta:
        icon = "arrow-left"
        label = "Back Button"


class LinkHoverStyleBlock(blocks.StructBlock):
    """
    A block for configuring link hover states in RichText blocks.
    """

    hover_color = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Link hover color",
    )
    hover_underline = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="Show underline on hover",
    )
    hover_opacity = blocks.DecimalBlock(
        required=False,
        min_value=0,
        max_value=1,
        decimal_places=2,
        help_text="Hover opacity (0-1)",
    )
    transition_duration = blocks.ChoiceBlock(
        choices=[
            ("0ms", "None"),
            ("150ms", "Fast"),
            ("300ms", "Normal"),
            ("500ms", "Slow"),
        ],
        default="150ms",
        help_text="Transition duration",
    )

    class Meta:
        icon = "link"
        label = "Link Hover Style"


class ProgrammaticPageStyleBlock(blocks.StructBlock):
    """
    A block for styling programmatic (non-Wagtail) pages like session forms.
    """

    page_identifier = blocks.ChoiceBlock(
        choices=[
            ("create_session", "Create Session"),
            ("edit_session", "Edit Session"),
            ("view_session", "View Session"),
            ("sessions_index", "Sessions Index"),
            ("manage_availability", "Manage Availability"),
            ("request_session", "Request Session"),
            ("payment_history", "Payment History"),
            ("payment_success", "Payment Success"),
        ],
        help_text="The page to customize",
    )
    heading_text = blocks.CharBlock(
        required=False,
        max_length=200,
        help_text="Custom heading text",
    )
    heading_color = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Heading color",
    )
    button_text = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Primary button text",
    )
    button_background_color = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Primary button background color",
    )
    button_text_color = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Primary button text color",
    )
    secondary_button_text = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Secondary button text",
    )
    background_color = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Page background color",
    )

    class Meta:
        icon = "doc-full"
        label = "Page Style"


class BorderStyleBlock(blocks.StructBlock):
    """
    A block for configuring border styles with tabbed organization.
    """

    style = blocks.ChoiceBlock(
        choices=[
            ("none", "None"),
            ("zigzag", "Zigzag"),
            ("wave", "Wave"),
            ("rounded", "Rounded"),
            ("legoWave", "Lego Wave"),
            ("leftCurve", "Left Curve"),
            ("rightCurve", "Right Curve"),
        ],
        default="none",
        help_text="Border style",
    )
    color = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Border color",
    )
    size = blocks.ChoiceBlock(
        choices=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        default="medium",
        help_text="Border size",
    )

    class Meta:
        icon = "form"
        label = "Border Style"


class FontChooserBlock(blocks.StructBlock):
    """
    Block for choosing a font with support for custom fonts from WebDesignSettings.
    """

    font_type = blocks.ChoiceBlock(
        choices=FONT_CHOICES,
        default="body",
        help_text="Select a root font or choose custom",
    )
    custom_font = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Custom font-family value (only used when 'Custom' is selected)",
    )

    class Meta:
        icon = "pilcrow"
        label = "Font"


class BorderBlock(blocks.StructBlock):
    """
    Border configuration block with tabbed organization for top and bottom borders.
    Provides visual separation between content sections.
    """

    style = blocks.ChoiceBlock(
        choices=BORDER_CHOICES,
        default="none",
        required=False,
        help_text="Border style",
    )
    color = ColorPickerBlock(
        required=False,
        help_text="Border color",
    )
    size = blocks.ChoiceBlock(
        choices=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        default="medium",
        required=False,
        help_text="Border size",
    )

    class Meta:
        icon = "form"
        label = "Border"
        collapsed = True


class StyledBlock(blocks.StructBlock):
    """
    Base block with common styling options for all content blocks.
    Uses ColorPickerBlock for dynamic color selection.
    """

    background_color = ColorPickerBlock(
        required=False,
        help_text="Background color for the block",
    )
    text_color = ColorPickerBlock(
        required=False,
        help_text="Text color for the block",
    )

    # Tabbed border customization
    top_border = BorderBlock(
        required=False,
        help_text="Top border configuration",
    )
    bottom_border = BorderBlock(
        required=False,
        help_text="Bottom border configuration",
    )

    # Back button configuration
    show_back_button = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Show a back button at the top of this section",
    )
    back_button_text = blocks.CharBlock(
        required=False,
        max_length=100,
        default="Back",
        help_text="Back button text",
    )
    back_button_link = blocks.URLBlock(
        required=False,
        help_text="Custom back link (leave blank for browser history)",
    )
    back_button_color = ColorPickerBlock(
        required=False,
        help_text="Back button text color",
    )

    class Meta:
        abstract = True


class StyledButtonBlock(StyledBlock):
    """
    Base block with common styling options for all content blocks with buttons.
    Uses ColorPickerBlock for dynamic color selection.
    """

    button_background_color = ColorPickerBlock(
        required=False,
        help_text="Background color for buttons in the block",
    )
    button_text_color = ColorPickerBlock(
        required=False,
        help_text="Text color for buttons in the block",
    )
    button_font = FontChooserBlock(
        required=False,
        help_text="Font for buttons in the block",
    )

    class Meta:
        abstract = True


class HeroBlock(StyledButtonBlock):
    """
    Full-width hero section with image, heading, subtitle, and CTA button.
    """

    image = ImageChooserBlock(required=False, help_text="Background image for the hero")
    heading = blocks.CharBlock(max_length=255, help_text="Main heading")
    subheading = blocks.CharBlock(
        max_length=500,
        required=False,
        help_text="Optional subtitle or tagline",
    )
    button_text = blocks.CharBlock(
        max_length=100,
        required=False,
        help_text="Text for the call-to-action button",
    )
    button_link = blocks.URLBlock(
        required=False,
        help_text="URL for the button to link to",
    )
    min_height = blocks.ChoiceBlock(
        choices=[
            ("300px", "Small (300px)"),
            ("500px", "Medium (500px)"),
            ("800px", "Large (800px)"),
        ],
        default="500px",
        help_text="Minimum height of the hero section",
    )

    class Meta:
        icon = "image"
        label = "Hero Section"
        collapsed = True
        template = "core/blocks/hero_block.html"


class TextBlock(StyledBlock):
    """
    Rich text content block with formatting options.
    """

    content = blocks.RichTextBlock(
        # features=[
        #     "h1",
        #     "h2",
        #     "h3",
        #     "bold",
        #     "italic",
        #     "link",
        #     "ol",
        #     "ul",
        #     "hr",
        #     "code",
        #     "blockquote",
        #     "font-family",
        #     "font-size",
        # ],
        help_text="Main content",
    )
    max_width = blocks.ChoiceBlock(
        choices=[
            ("full", "Full Width"),
            ("1200px", "1200px"),
            ("900px", "900px"),
        ],
        default="900px",
    )

    class Meta:
        icon = "pilcrow"
        label = "Text Content"
        collapsed = True
        template = "core/blocks/text_block.html"


class TextImageBlock(StyledBlock):
    """
    Two-column block with text on one side and image on the other.
    """

    heading = blocks.CharBlock(
        max_length=255,
        required=False,
        help_text="Optional section heading",
    )
    text = blocks.RichTextBlock(
        # features=[
        #     "h2",
        #     "h3",
        #     "bold",
        #     "italic",
        #     "link",
        #     "ol",
        #     "ul",
        #     "blockquote",
        #     "font-family",
        #     "font-size",
        # ],
        help_text="Content text",
    )
    image = ImageChooserBlock(help_text="Side-by-side image")
    image_position = blocks.ChoiceBlock(
        choices=[
            ("left", "Image on Left"),
            ("right", "Image on Right"),
        ],
        default="right",
    )

    class Meta:
        icon = "image"
        label = "Text + Image"
        collapsed = True
        template = "core/blocks/text_image_block.html"


class CTABlock(StyledButtonBlock):
    """
    Call-to-action section with prominent button.
    """

    heading = blocks.CharBlock(
        max_length=255,
        help_text="Heading for the CTA section",
    )
    description = blocks.TextBlock(
        required=False,
        help_text="Optional description text",
    )
    button_text = blocks.CharBlock(
        max_length=100,
        help_text="Text for the main button",
    )
    button_link = blocks.URLBlock(help_text="URL for the button")

    class Meta:
        icon = "link"
        label = "Call-to-Action"
        collapsed = True
        template = "core/blocks/cta_block.html"


class TestimonialBlock(StyledBlock):
    """
    Testimonial quote with author attribution.
    """

    quote = blocks.TextBlock(
        max_length=1000,
        help_text="The testimonial text",
    )
    author_name = blocks.CharBlock(
        max_length=255,
        help_text="Name of the person giving the testimonial",
    )
    author_title = blocks.CharBlock(
        max_length=255,
        required=False,
        help_text="Title or role of the author (e.g., 'Peer Support Specialist')",
    )
    author_image = ImageChooserBlock(
        required=False,
        help_text="Author's profile image",
    )
    rating = blocks.IntegerBlock(
        min_value=1,
        max_value=5,
        required=False,
        help_text="Star rating (1-5)",
    )

    class Meta:
        icon = "openquote"
        label = "Testimonial"
        collapsed = True
        template = "core/blocks/testimonial_block.html"


class FeatureGridBlock(StyledBlock):
    """
    Grid of feature cards with icons/images and descriptions.
    """

    heading = blocks.CharBlock(
        max_length=255,
        required=False,
        help_text="Optional section heading",
    )
    features = blocks.StreamBlock(
        [
            (
                "feature",
                blocks.StructBlock(
                    [
                        ("title", blocks.CharBlock(max_length=100)),
                        (
                            "description",
                            blocks.TextBlock(max_length=500),
                        ),
                        (
                            "icon",
                            EmojiChooserBlock(
                                required=False,
                                help_text="Optional icon for the feature",
                            ),
                        ),
                    ]
                ),
            )
        ],
        max_num=6,
        help_text="Add up to 6 features",
    )
    columns = blocks.ChoiceBlock(
        choices=[
            ("2", "2 columns"),
            ("3", "3 columns"),
            ("4", "4 columns"),
        ],
        default="3",
    )

    class Meta:
        icon = "grip"
        label = "Feature Grid"
        collapsed = True
        template = "core/blocks/feature_grid_block.html"


class FAQBlock(StyledBlock):
    """
    Frequently Asked Questions accordion.
    """

    heading = blocks.CharBlock(
        max_length=255,
        required=False,
        help_text="Optional section heading",
    )
    items = blocks.StreamBlock(
        [
            (
                "faq_item",
                blocks.StructBlock(
                    [
                        ("question", blocks.CharBlock(max_length=255)),
                        (
                            "answer",
                            blocks.RichTextBlock(
                                # features=[
                                #     "bold",
                                #     "italic",
                                #     "link",
                                #     "ol",
                                #     "ul",
                                #     "font-family",
                                #     "font-size",
                                # ]
                            ),
                        ),
                    ]
                ),
            )
        ],
        help_text="Add FAQ items",
    )

    class Meta:
        icon = "help"
        label = "FAQ/Accordion"
        collapsed = True
        template = "core/blocks/faq_block.html"


class SpacerBlock(StyledBlock):
    """
    Empty block for adding vertical spacing between sections.
    """

    height = blocks.ChoiceBlock(
        choices=[
            ("20px", "Small"),
            ("40px", "Medium"),
            ("60px", "Large"),
            ("100px", "Extra Large"),
        ],
        default="40px",
    )

    class Meta:
        icon = "arrow-down"
        label = "Spacer"
        collapsed = True
        template = "core/blocks/spacer_block.html"


class GridBlock(StyledBlock):
    """
    Generic grid block for flexible layouts.
    """

    items = blocks.StreamBlock(
        [
            (
                "grid_item",
                blocks.StreamBlock(
                    [
                        ("hero", HeroBlock()),
                        ("text", TextBlock()),
                        ("text_image", TextImageBlock()),
                        ("cta", CTABlock()),
                        ("testimonial", TestimonialBlock()),
                        ("features", FeatureGridBlock()),
                        ("faq", FAQBlock()),
                        ("spacer", SpacerBlock()),
                    ]
                ),
            )
        ],
        help_text="Add items to the grid",
    )
    columns = blocks.ChoiceBlock(
        choices=[
            ("2", "2 columns"),
            ("3", "3 columns"),
            ("4", "4 columns"),
        ],
        default="2",
    )

    class Meta:
        icon = "grip"
        label = "Generic Grid"
        collapsed = True
        template = "core/blocks/grid_block.html"


class MarqueeBlock(StyledBlock):
    """
    Marquee block for scrolling text or images.
    """

    content = blocks.CharBlock(
        max_length=255,
        help_text="Text to scroll in the marquee",
    )
    repeat = blocks.IntegerBlock(
        min_value=-1,
        max_value=10,
        default=-1,
        help_text="Number of times to repeat the marquee content. Set to -1 for infinite repetition.",
    )
    size = blocks.ChoiceBlock(
        choices=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        default="medium",
    )
    speed = blocks.ChoiceBlock(
        choices=[
            ("slow", "Slow"),
            ("medium", "Medium"),
            ("fast", "Fast"),
        ],
        default="medium",
    )

    class Meta:
        icon = "move"
        label = "Marquee"
        collapsed = True
        template = "core/blocks/marquee_block.html"


class LinkHoverStyleBlock(blocks.StructBlock):
    """
    Block for configuring link hover states in RichText content.
    Allows admins to customize how links appear on hover.
    """

    hover_color = ColorPickerBlock(
        required=False,
        help_text="Link hover color (leave blank for default darkening)",
    )
    hover_underline = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="Show underline on hover",
    )
    hover_opacity = blocks.DecimalBlock(
        required=False,
        min_value=0,
        max_value=1,
        decimal_places=2,
        help_text="Hover opacity (0-1, leave blank for full opacity)",
    )
    transition_duration = blocks.ChoiceBlock(
        choices=[
            ("0ms", "None"),
            ("150ms", "Fast"),
            ("300ms", "Normal"),
            ("500ms", "Slow"),
        ],
        default="150ms",
        required=False,
        help_text="Transition duration for hover effects",
    )

    class Meta:
        icon = "link"
        label = "Link Hover Style"


class StyledRichTextBlock(StyledBlock):
    """
    Rich text content block with link hover customization.
    Extends StyledBlock with RichText content and link styling options.
    """

    content = blocks.RichTextBlock(
        # features=[
        #     "h1",
        #     "h2",
        #     "h3",
        #     "bold",
        #     "italic",
        #     "link",
        #     "ol",
        #     "ul",
        #     "hr",
        #     "code",
        #     "blockquote",
        #     "font-family",
        #     "font-size",
        # ],
        help_text="Main content",
    )
    link_color = ColorPickerBlock(
        required=False,
        help_text="Default link color",
    )
    link_hover_style = LinkHoverStyleBlock(
        required=False,
        help_text="Customize how links appear on hover",
    )
    max_width = blocks.ChoiceBlock(
        choices=[
            ("full", "Full Width"),
            ("1200px", "1200px"),
            ("900px", "900px"),
        ],
        default="900px",
    )

    class Meta:
        icon = "pilcrow"
        label = "Styled Rich Text"
        collapsed = True
        template = "core/blocks/styled_rich_text_block.html"


class BlogFeedBlock(StyledBlock):
    """
    Block for displaying a blog feed on any page.
    Only shows blog posts when this block is present.
    """

    heading = blocks.CharBlock(
        max_length=255,
        required=False,
        default="Latest Posts",
        help_text="Optional heading for the blog feed",
    )
    heading_font = FontChooserBlock(
        required=False,
        help_text="Font for the heading",
    )
    heading_color = ColorPickerBlock(
        required=False,
        help_text="Heading color",
    )
    max_posts = blocks.IntegerBlock(
        min_value=1,
        max_value=50,
        default=10,
        help_text="Maximum number of posts to display",
    )
    show_date = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="Show post date",
    )
    show_excerpt = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="Show post excerpt/intro",
    )
    empty_message = blocks.CharBlock(
        max_length=255,
        required=False,
        default="No blog posts yet.",
        help_text="Message to display when no posts are available",
    )
    link_color = ColorPickerBlock(
        required=False,
        help_text="Link color for blog post titles",
    )
    link_hover_style = LinkHoverStyleBlock(
        required=False,
        help_text="Customize how links appear on hover",
    )

    class Meta:
        icon = "doc-full"
        label = "Blog Feed"
        collapsed = True
        template = "core/blocks/blog_feed_block.html"


class BackButtonBlock(StyledBlock):
    """
    A dedicated back button block for placing a customizable back button.
    Can be added to any page's StreamField.
    """

    text = blocks.CharBlock(
        required=False,
        max_length=100,
        default="Back",
        help_text="Button text",
    )
    link = blocks.URLBlock(
        required=False,
        help_text="Custom link URL (leave blank to use browser history)",
    )
    position = blocks.ChoiceBlock(
        choices=[
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        default="left",
        help_text="Button position",
    )
    font = FontChooserBlock(
        required=False,
        help_text="Button font",
    )
    button_text_color = ColorPickerBlock(
        required=False,
        help_text="Button text color",
    )
    button_background_color = ColorPickerBlock(
        required=False,
        help_text="Button background color",
    )
    show_icon = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="Show arrow icon",
    )

    class Meta:
        icon = "arrow-left"
        label = "Back Button"
        collapsed = True
        template = "core/blocks/back_button_block.html"
        template = "core/blocks/back_button_block.html"
