"""
Reusable StreamField blocks for Wagtail page building.

These blocks provide flexible, composable components for content editors
to build pages without coding, similar to Squarespace/Webflow.
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class HeroBlock(blocks.StructBlock):
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
    background_color = blocks.ChoiceBlock(
        choices=[
            ("white", "White"),
            ("blue", "Blue"),
            ("navy", "Navy Blue"),
            ("gray", "Light Gray"),
            ("black", "Black"),
        ],
        default="white",
        help_text="Background color for the hero section",
    )
    text_color = blocks.ChoiceBlock(
        choices=[
            ("white", "White"),
            ("black", "Black"),
            ("blue", "Blue"),
            ("gray", "Dark Gray"),
        ],
        default="black",
        help_text="Text color for heading and subheading",
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


class TextBlock(blocks.StructBlock):
    """
    Rich text content block with formatting options.
    """

    content = blocks.RichTextBlock(
        features=[
            "h1",
            "h2",
            "h3",
            "bold",
            "italic",
            "link",
            "ol",
            "ul",
            "hr",
            "code",
            "blockquote",
        ],
        help_text="Main content",
    )
    background_color = blocks.ChoiceBlock(
        choices=[
            ("white", "White"),
            ("light-gray", "Light Gray"),
            ("blue-light", "Light Blue"),
        ],
        default="white",
        required=False,
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


class TextImageBlock(blocks.StructBlock):
    """
    Two-column block with text on one side and image on the other.
    """

    heading = blocks.CharBlock(
        max_length=255,
        required=False,
        help_text="Optional section heading",
    )
    text = blocks.RichTextBlock(
        features=[
            "h2",
            "h3",
            "bold",
            "italic",
            "link",
            "ol",
            "ul",
            "blockquote",
        ],
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
    background_color = blocks.ChoiceBlock(
        choices=[
            ("white", "White"),
            ("light-gray", "Light Gray"),
            ("blue-light", "Light Blue"),
        ],
        default="white",
        required=False,
    )

    class Meta:
        icon = "image"
        label = "Text + Image"
        collapsed = True
        template = "core/blocks/text_image_block.html"


class CTABlock(blocks.StructBlock):
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
    button_style = blocks.ChoiceBlock(
        choices=[
            ("primary", "Primary (Blue)"),
            ("secondary", "Secondary (Gray)"),
            ("success", "Success (Green)"),
        ],
        default="primary",
    )
    background_color = blocks.ChoiceBlock(
        choices=[
            ("white", "White"),
            ("navy", "Navy Blue"),
            ("light-gray", "Light Gray"),
        ],
        default="navy",
    )
    text_color = blocks.ChoiceBlock(
        choices=[
            ("white", "White"),
            ("black", "Black"),
            ("blue", "Blue"),
        ],
        default="white",
    )

    class Meta:
        icon = "link"
        label = "Call-to-Action"
        collapsed = True
        template = "core/blocks/cta_block.html"


class TestimonialBlock(blocks.StructBlock):
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


class FeatureGridBlock(blocks.StructBlock):
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
                            blocks.ChoiceBlock(
                                choices=[
                                    ("heart", "Heart"),
                                    ("users", "Users"),
                                    ("lock", "Lock"),
                                    ("bell", "Bell"),
                                    ("checkmark", "Checkmark"),
                                    ("star", "Star"),
                                ]
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
    background_color = blocks.ChoiceBlock(
        choices=[
            ("white", "White"),
            ("light-gray", "Light Gray"),
        ],
        default="white",
        required=False,
    )

    class Meta:
        icon = "grip"
        label = "Feature Grid"
        collapsed = True
        template = "core/blocks/feature_grid_block.html"


class FAQBlock(blocks.StructBlock):
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
                                features=[
                                    "bold",
                                    "italic",
                                    "link",
                                    "ol",
                                    "ul",
                                ]
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


class SpacerBlock(blocks.StructBlock):
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
