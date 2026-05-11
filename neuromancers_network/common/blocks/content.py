from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail_link_block.blocks import LinkBlock

from .base import BorderBlock
from .base import ThemedBlock
from .base import ThemedTypographyBlock

ALIGNMENT_CHOICES = [
    ("normal", _("Normal (default)")),
    ("center", _("Center aligned")),
    ("flex-start", _("Left aligned")),
    ("flex-end", _("Right aligned")),
    ("stretch", _("Stretch to fill")),
]

JUSTIFY_CHOICES = [
    *ALIGNMENT_CHOICES,
    ("space-between", _("Space between")),
    ("space-around", _("Space around")),
    ("space-evenly", _("Space evenly")),
]

INLINE_SIZE_CHOICES = [
    ("auto", _("Auto (width determined by content)")),
    ("narrow", _("Narrow")),
    ("medium", _("Medium")),
    ("wide", _("Wide")),
    ("widest", _("Widest (with some margin)")),
]

SIZE_CHOICES = [
    *INLINE_SIZE_CHOICES,
    ("screen", _("Full width (screen)")),
]

VISIBLE_TO_ALL = 0
VISIBLE_TO_SEEKERS = 1
VISIBLE_TO_PEERS = 2
VISIBLE_TO_VERIFIED_PEERS = 3
VISIBLE_TO_ADMINS = 4
VISIBLE_TO_OWNER = 5

USER_GROUP_CHOICES = [
    (
        VISIBLE_TO_OWNER,
        _("Owner only (only visible to the user who created the content)"),
    ),
    (VISIBLE_TO_ADMINS, _("Admin")),
    (VISIBLE_TO_VERIFIED_PEERS, _("Verified Peer")),
    (VISIBLE_TO_PEERS, _("Peer")),
    (VISIBLE_TO_SEEKERS, _("Seeker")),
    (VISIBLE_TO_ALL, _("All users")),
]


class CalendarBlock(blocks.StructBlock):
    """A block that renders a monthly calendar with session events."""

    show_as = blocks.ChoiceBlock(
        choices=[
            ("month", _("Month view")),
            ("week", _("Week view")),
        ],
        default="month",
    )
    show_filters = blocks.BooleanBlock(
        default=True,
        required=False,
        label=_("Show filters"),
    )
    max_events = blocks.IntegerBlock(
        default=0,
        required=False,
        help_text=_("Max events per day (0 = show all)"),
    )

    class Meta:
        template = "common/blocks/calendar.html"
        icon = "date"
        label = _("Calendar")


class PermissionBlock:
    """
    A block representing a permission setting, used for controlling access to
    content based on user groups.
    """

    restrict_to_user_groups = blocks.MultipleChoiceBlock(
        choices=USER_GROUP_CHOICES,
        help_text=_("The user group that has permission to view this content."),
        default=[VISIBLE_TO_ALL],
    )

    class Meta:
        abstract = True


class SectionBlock(ThemedBlock, PermissionBlock):
    """
    A block representing a section of content, with optional background and
    styling.  Used in StreamFields across the site to allow flexible page
    building.
    """

    width = blocks.ChoiceBlock(
        choices=SIZE_CHOICES,
        default="wide",
        help_text=_("Width of the content section."),
    )
    height = blocks.ChoiceBlock(
        choices=SIZE_CHOICES,
        default="auto",
        help_text=_("Height of the content section."),
    )
    fixed_width = blocks.IntegerBlock(
        null=True,
        blank=True,
        help_text=_("Set a fixed width in pixels (overrides width choice)"),
    )
    fixed_height = blocks.IntegerBlock(
        null=True,
        blank=True,
        help_text=_("Set a fixed height in pixels (overrides height choice)"),
    )

    class Meta:
        abstract = True


class InlineBlock(ThemedTypographyBlock, PermissionBlock):
    """
    A block representing an inline element within a section, with optional
    """

    width = blocks.ChoiceBlock(
        choices=INLINE_SIZE_CHOICES,
        default="wide",
        help_text=_("Width of the inline block."),
    )
    height = blocks.ChoiceBlock(
        choices=INLINE_SIZE_CHOICES,
        default="auto",
        help_text=_("Height of the inline block."),
    )
    fixed_width = blocks.IntegerBlock(
        null=True,
        blank=True,
        help_text=_("Set a fixed width in pixels (overrides width choice)"),
    )
    fixed_height = blocks.IntegerBlock(
        null=True,
        blank=True,
        help_text=_("Set a fixed height in pixels (overrides height choice)"),
    )

    class Meta:
        abstract = True


class InlineTextBlock(InlineBlock):
    """
    A block representing a piece of text within a section, with optional styling.
    """

    text = blocks.CharBlock(
        max_length=255,
        help_text=_("Text content for the inline block."),
        blank=True,
    )

    def __init__(self, *args, **kwargs):
        max_length = kwargs.pop("max_length", None)
        super().__init__(*args, **kwargs)
        if isinstance(max_length, int) and "text" in self.child_blocks:
            self.child_blocks["text"].field.max_length = max_length

    # Allow text max length to be overridden in specific block types that
    # inherit from this one, e.g. MarqueeBlock
    class Meta:
        icon = "tag"
        group = _("Inline Block")
        collapsed = True


class InlineLinkBlock(InlineTextBlock):
    """
    A block representing a piece of text with an optional link, used for inline
    links within a section.
    """

    link = LinkBlock(help_text=_("URL or internal page to link to"))

    class Meta:
        icon = "link"
        group = _("Inline Link")
        collapsed = True


class InlineRichTextBlock(InlineBlock):
    """
    A block representing a piece of rich text within a section, with optional styling.
    """

    text = blocks.RichTextBlock(
        help_text=_("Rich text content for the inline block."),
        blank=True,
    )

    class Meta:
        icon = "doc-full"
        group = _("Inline Rich Text Block")
        collapsed = True


class AttributeBlock(InlineBlock):
    """
    A block representing a model attribute, used for dynamically displaying fields from a model instance.
    """

    MODEL_CHOICES = [
        ("users.user", _("User")),
        ("users.profile", _("Profile")),
        ("events.session", _("Session")),
        ("events.sessionbooking", _("Session Booking")),
        ("events.sessionprice", _("Session Price")),
    ]

    model = blocks.ChoiceBlock(
        choices=MODEL_CHOICES,
        help_text=_(
            "The model to pull the attribute from, in the format 'app_label.ModelName'.",
        ),
    )
    model_field = blocks.CharBlock(
        help_text=_("The name of the attribute to display."),
    )

    class Meta:
        icon = "info-circle"
        group = _("Attribute")
        collapsed = True
        template = "common/blocks/attribute.html"


class CopyrightBlock(InlineTextBlock):
    """
    A block representing a copyright notice, with optional styling.
    """

    text = blocks.CharBlock(
        max_length=512,
        help_text=_(
            "Copyright text. This will sit alongside the copyright symbol and current year, so should just be the name of the copyright holder or similar.",
        ),
        blank=True,
    )

    class Meta:
        icon = "calendar-alt"
        group = _("Copyright")
        collapsed = True
        template = "common/blocks/copyright.html"


class ImageBlock(InlineBlock):
    """
    A block representing an image, with optional styling.
    """

    image = ImageChooserBlock(help_text=_("Image to display"))

    class Meta:
        icon = "image"
        group = _("Image")
        collapsed = True
        template = "common/blocks/image.html"


class ButtonBlock(InlineTextBlock):
    """
    A block representing a button or link, with optional styling.
    """

    link = LinkBlock(help_text=_("URL or internal page to link to"), required=False)

    class Meta:
        icon = "link"
        group = _("Button")
        collapsed = True
        template = "common/blocks/button.html"


class HeaderBlock(InlineTextBlock):
    """
    A block representing a header, with optional styling.
    """

    class Meta:
        icon = "title"
        group = _("Header")
        collapsed = True
        template = "common/blocks/header.html"


class MarqueeBlock(SectionBlock):
    """
    A block representing a marquee (scrolling text), with optional styling.
    """

    SPEED_CHOICES = [
        ("slow", _("Slow")),
        ("medium", _("Medium")),
        ("fast", _("Fast")),
    ]

    DIRECTION_CHOICES = [
        ("left", _("Left to right")),
        ("right", _("Right to left")),
        ("up", _("Bottom to top")),
        ("down", _("Top to bottom")),
    ]

    speed = blocks.ChoiceBlock(
        choices=SPEED_CHOICES,
        default="medium",
        help_text=_("Speed of the marquee animation."),
    )

    text = blocks.CharBlock(
        max_length=255,
        help_text=_("Text content for the marquee."),
        blank=True,
    )

    direction = blocks.ChoiceBlock(
        choices=DIRECTION_CHOICES,
        default="right",
        help_text=_("Direction of the marquee animation."),
    )

    class Meta:
        icon = "dots-horizontal"
        group = _("Marquee")
        collapsed = True
        template = "common/blocks/marquee.html"


BASE_CONTENT_BLOCKS = [
    ("image", ImageBlock()),
    ("header", HeaderBlock()),
    ("text", InlineTextBlock()),
    ("rich_text", InlineRichTextBlock()),
    ("button", ButtonBlock()),
    ("link", InlineLinkBlock()),
    ("attribute", AttributeBlock()),
]


class InlineCardBlock(InlineBlock):
    """
    A block representing a card, with optional image, text, and link, designed
    for inline use within a section.
    """

    content = blocks.StreamBlock(
        BASE_CONTENT_BLOCKS,
        label=_("Card content"),
    )

    class Meta:
        icon = "minus"
        group = _("Inline Card")
        collapsed = True
        template = "common/blocks/inline_card.html"


INLINE_CONTENT_BLOCKS = [
    *BASE_CONTENT_BLOCKS,
    ("inline_card", InlineCardBlock()),
]


class CardBlock(SectionBlock):
    """
    A block representing a card, with optional image, text, and link.
    """

    content = blocks.StreamBlock(
        INLINE_CONTENT_BLOCKS,
        label=_("Card content"),
    )

    class Meta:
        icon = "bars"
        group = _("Card")
        collapsed = True
        template = "common/blocks/card.html"


CONTENT_BLOCKS = [
    *INLINE_CONTENT_BLOCKS,
    ("card", CardBlock()),
]


class AccordionItemBlock(blocks.StructBlock):
    """
    A block representing a single item within an accordion, with a heading and
    content.
    """

    heading = HeaderBlock()
    content = blocks.StreamBlock(
        CONTENT_BLOCKS,
        label=_("Accordion item content"),
    )
    collapsed_icon = InlineTextBlock(
        max_length=10,
        help_text=_("Icon for collapsed state (overrides accordion default)"),
        default="plus",
    )
    expanded_icon = InlineTextBlock(
        max_length=10,
        help_text=_("Icon for expanded state (overrides accordion default)"),
        default="minus",
    )
    border = BorderBlock(
        help_text=_("Border style for this item (overrides accordion default)"),
    )

    class Meta:
        icon = "plus"
        group = _("Accordion Item")
        collapsed = True
        template = "common/blocks/accordion_item.html"


class AccordionBlock(SectionBlock):
    """
    A block representing an accordion, with multiple items that can be expanded
    or collapsed.
    """

    items = blocks.ListBlock(AccordionItemBlock(), label=_("Accordion items"))
    default_item_border = BorderBlock(
        help_text=_(
            "Default border style for accordion items (can be overridden per item)",
        ),
    )
    default_item_collapsed_icon = InlineTextBlock(
        max_length=10,
        help_text=_("Default icon for collapsed items (can be overridden per item)"),
        default="plus",
    )
    default_item_expanded_icon = InlineTextBlock(
        max_length=10,
        help_text=_("Default icon for expanded items (can be overridden per item)"),
        default="minus",
    )

    class Meta:
        icon = "placeholder"
        group = _("Accordion")
        collapsed = True
        template = "common/blocks/accordion.html"


class SpacedBlock(SectionBlock):
    """
    A block representing a spacer, used to create space between sections.
    """

    spacing = blocks.IntegerBlock(
        default=16,
        help_text=_("Amount of space in pixels."),
    )
    content = blocks.StreamBlock(
        CONTENT_BLOCKS,
        label=_("Content"),
    )
    scale_items_to_fill = blocks.BooleanBlock(
        default=False,
        help_text=_("Scale items to fill any available space."),
    )

    class Meta:
        abstract = True


class ListBlock(SpacedBlock):
    """
    A block representing a list of items, with optional styling.
    """

    LIST_ORDERING_CHOICES = [
        ("unordered", _("Unordered")),
        ("ordered", _("Ordered")),
    ]
    heading = HeaderBlock(required=False)
    ordering = blocks.ChoiceBlock(
        choices=LIST_ORDERING_CHOICES,
        default="unordered",
        help_text=_("Whether the list is ordered (numbered) or unordered."),
    )
    list_marker_style = InlineBlock(
        help_text=_("Styling for list markers (bullets or numbers)."),
    )

    class Meta:
        icon = "list-ul"
        group = _("List")
        collapsed = True
        template = "common/blocks/list.html"


class LinkListBlock(SpacedBlock):
    """
    A block representing a list of links, with optional styling.
    """

    heading = HeaderBlock(required=False)
    content = blocks.ListBlock(
        InlineLinkBlock(),
        label=_("Links"),
    )

    class Meta:
        icon = "link"
        group = _("Link List")
        collapsed = True
        template = "common/blocks/list.html"


LIST_CONTENT_BLOCKS = [
    *CONTENT_BLOCKS,
    ("list", ListBlock()),
    ("link_list", LinkListBlock()),
]


class SpacedBlockWithList(SpacedBlock):
    """
    A block representing a section with a list of items, with optional styling.
    """

    content = blocks.StreamBlock(
        LIST_CONTENT_BLOCKS,
        label=_("Content"),
    )

    class Meta:
        abstract = True


class Row:
    horizontal_alignment = blocks.ChoiceBlock(
        choices=JUSTIFY_CHOICES,
        default="normal",
        help_text=_("Horizontal alignment of items within the row."),
    )

    vertical_alignment = blocks.ChoiceBlock(
        choices=ALIGNMENT_CHOICES,
        default="normal",
        help_text=_("Vertical alignment of items within the row."),
    )

    class Meta:
        abstract = True


class Column:
    horizontal_alignment = blocks.ChoiceBlock(
        choices=ALIGNMENT_CHOICES,
        default="normal",
        help_text=_("Horizontal alignment of items within the column."),
    )

    vertical_alignment = blocks.ChoiceBlock(
        choices=JUSTIFY_CHOICES,
        default="normal",
        help_text=_("Vertical alignment of items within the column."),
    )

    class Meta:
        abstract = True


class Grid:
    horizontal_alignment = blocks.ChoiceBlock(
        choices=JUSTIFY_CHOICES,
        default="normal",
        help_text=_("Horizontal alignment of items within the grid."),
    )

    vertical_alignment = blocks.ChoiceBlock(
        choices=JUSTIFY_CHOICES,
        default="normal",
        help_text=_("Vertical alignment of items within the grid."),
    )

    num_columns = blocks.IntegerBlock(
        default=2,
        min_value=1,
        max_value=6,
        help_text=_("Number of columns in the grid."),
    )

    num_rows = blocks.IntegerBlock(
        default=2,
        min_value=1,
        max_value=6,
        help_text=_("Number of rows in the grid."),
    )

    class Meta:
        abstract = True


class RowBlock(SpacedBlockWithList, Row):
    """
    A block representing a row of content, with optional spacing and alignment.
    """

    class Meta:
        icon = "expand-right"
        group = _("Row")
        collapsed = True
        template = "common/blocks/row.html"


class ColumnBlock(SpacedBlockWithList, Column):
    """
    A block representing a column of content, with optional spacing and alignment.
    """

    class Meta:
        icon = "collapse-down"
        group = _("Column")
        collapsed = True
        template = "common/blocks/column.html"


class GridBlock(SpacedBlockWithList, Grid):
    """
    A block representing a grid of content, with optional spacing and alignment.
    """

    class Meta:
        icon = "grid"
        group = _("Grid")
        collapsed = True
        template = "common/blocks/grid.html"


ALL_CONTENT_BLOCKS = [
    *LIST_CONTENT_BLOCKS,
    ("accordion", AccordionBlock()),
    ("row", RowBlock()),
    ("column", ColumnBlock()),
    ("grid", GridBlock()),
    ("marquee", MarqueeBlock()),
    ("copyright", CopyrightBlock()),
    ("calendar", CalendarBlock()),
]


class ContentBlock(blocks.StreamBlock):
    """
    A block representing a piece of content, with optional styling and layout.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("local_blocks", ALL_CONTENT_BLOCKS)
        super().__init__(*args, **kwargs)

    class Meta:
        icon = "plus-inverse"
        group = _("Content")
        collapsed = True
        template = "common/blocks/content.html"
