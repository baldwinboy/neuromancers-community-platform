import logging

from django.apps import apps
from django.db import models
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.images.blocks import ImageChooserBlock
from wagtail_color_panel.blocks import NativeColorBlock
from wagtail_color_panel.widgets import ColorInputWidget


class ColorScheme(models.TextChoices):
    LIGHT = "light", _("Light mode")
    DARK = "dark", _("Dark mode")


class GradientDirections(models.IntegerChoices):
    LEFT_TO_RIGHT = 90, _("Left to right")
    RIGHT_TO_LEFT = -90, _("Right to left")
    TOP_TO_BOTTOM = 0, _("Top to bottom")
    BOTTOM_TO_TOP = 180, _("Bottom to top")
    DIAGONAL_LEFT_TO_RIGHT = 45, _("Diagonal left to right")
    DIAGONAL_RIGHT_TO_LEFT = -45, _("Diagonal right to left")


class FontWeights(models.IntegerChoices):
    THIN = 100, _("Thin")
    EXTRA_LIGHT = 200, _("Extra-light")
    LIGHT = 300, _("Light")
    NORMAL = 400, _("Normal")
    MEDIUM = 500, _("Medium")
    SEMI_BOLD = 600, _("Semi-bold")
    BOLD = 700, _("Bold")
    EXTRA_BOLD = 800, _("Extra-bold")
    BLACK = 900, _("Black")


class FontStyles(models.TextChoices):
    NORMAL = "normal", _("Normal")
    ITALIC = "italic", _("Italic")
    OBLIQUE = "oblique", _("Oblique")


class TextAlignment(models.TextChoices):
    LEFT = "left", _("Left")
    CENTER = "center", _("Center")
    RIGHT = "right", _("Right")
    JUSTIFY = "justify", _("Justify")


class Sides(models.TextChoices):
    LEFT = "left", _("Left")
    RIGHT = "right", _("Right")
    TOP = "top", _("Top")
    BOTTOM = "bottom", _("Bottom")


class BorderStyles(models.TextChoices):
    SOLID = "solid", _("Solid")
    DASHED = "dashed", _("Dashed")
    DOTTED = "dotted", _("Dotted")
    DOUBLE = "double", _("Double")
    GROOVE = "groove", _("Groove")
    RIDGE = "ridge", _("Ridge")
    INSET = "inset", _("Inset")
    OUTSET = "outset", _("Outset")


COLOR_LABELS = {
    "base_100": _("Base-100"),
    "base_200": _("Base-200"),
    "base_300": _("Base-300"),
    "base_content": _("Base Content"),
    "primary": _("Primary"),
    "primary_content": _("Primary Content"),
    "secondary": _("Secondary"),
    "secondary_content": _("Secondary Content"),
    "accent": _("Accent"),
    "accent_content": _("Accent Content"),
    "neutral": _("Neutral"),
    "neutral_content": _("Neutral Content"),
    "info": _("Info"),
    "info_content": _("Info Content"),
    "success": _("Success"),
    "success_content": _("Success Content"),
    "warning": _("Warning"),
    "warning_content": _("Warning Content"),
    "error": _("Error"),
    "error_content": _("Error Content"),
}

COLOR_GROUPS = [
    (
        _("Base Surfaces"),
        [
            "base_100",
            "base_200",
            "base_300",
            "base_content",
        ],
    ),
    (
        _("Brand"),
        [
            "primary",
            "primary_content",
            "secondary",
            "secondary_content",
            "accent",
            "accent_content",
        ],
    ),
    (_("Neutral"), ["neutral", "neutral_content"]),
    (
        _("Semantic"),
        [
            "info",
            "info_content",
            "success",
            "success_content",
            "warning",
            "warning_content",
            "error",
            "error_content",
        ],
    ),
]

LIGHT_MODE_DEFAULT_COLORS = {
    "base_100": "#F5D0FF",
    "base_200": "#fbcfe8",
    "base_300": "#e84a7a",
    "base_content": "#0f0a1a",
    "primary": "#F5D0FF",
    "primary_content": "#0f0a1a",
    "secondary": "#fbcfe8",
    "secondary_content": "#1a0a1f",
    "accent": "#7c3aed",
    "accent_content": "#e84a7a",
    "neutral": "#4a1942",
    "neutral_content": "#e84a7a",
    "info": "#fbcfe8",
    "info_content": "#e84a7a",
    "success": "#d1fae5",
    "success_content": "#10b981",
    "warning": "#fef3c7",
    "warning_content": "#f59e0b",
    "error": "#fee2e2",
    "error_content": "#ef4444",
}

DARK_MODE_DEFAULT_COLORS = {
    "base_100": "#0F0A1A",
    "base_200": "#1A0A1F",
    "base_300": "#4a1942",
    "base_content": "#FDF2F8",
    "primary": "#0F0A1A",
    "primary_content": "#FDF2F8",
    "secondary": "#1A0A1F",
    "secondary_content": "#FBCFE8",
    "accent": "#7c3aed",
    "accent_content": "#e84a7a",
    "neutral": "#4a1942",
    "neutral_content": "#e84a7a",
    "info": "#fbcfe8",
    "info_content": "#e84a7a",
    "success": "#d1fae5",
    "success_content": "#10b981",
    "warning": "#fef3c7",
    "warning_content": "#f59e0b",
    "error": "#fee2e2",
    "error_content": "#ef4444",
}

# --- COLOR PALETTE ---


class ColorPaletteBlock(blocks.StructBlock):
    """
    A block for defining a full daisyUI 5 colour palette with mode, semantic
    colours, radii, sizes, border, and effects.  Matches the CSS custom
    properties that daisyUI expects so that the admin-configured palette
    feeds directly into the daisyUI theme system.

    DaisyUI 5 variable reference:
      https://daisyui.com/docs/config/
    """

    # -- Base surface colours -------------------------------------------------
    base_100 = NativeColorBlock(default="#ffffff", help_text=_("Base surface colour"))
    base_200 = NativeColorBlock(default="#f3f4f6", help_text=_("Darker base shade"))
    base_300 = NativeColorBlock(
        default="#e5e7eb",
        help_text=_("Even darker base shade"),
    )
    base_content = NativeColorBlock(
        default="#1f2937",
        help_text=_("Foreground content on base"),
    )

    # -- Brand colours --------------------------------------------------------
    primary = NativeColorBlock(default="#F5D0FF", help_text=_("Primary brand colour"))
    primary_content = NativeColorBlock(
        default="#4a005f",
        help_text=_("Content on primary"),
    )
    secondary = NativeColorBlock(
        default="#FBCFE9",
        help_text=_("Secondary brand colour"),
    )
    secondary_content = NativeColorBlock(
        default="#4a0030",
        help_text=_("Content on secondary"),
    )
    accent = NativeColorBlock(default="#7C3AED", help_text=_("Accent colour"))
    accent_content = NativeColorBlock(
        default="#ffffff",
        help_text=_("Content on accent"),
    )
    neutral = NativeColorBlock(default="#6b7280", help_text=_("Neutral colour"))
    neutral_content = NativeColorBlock(
        default="#ffffff",
        help_text=_("Content on neutral"),
    )

    # -- Semantic colours -----------------------------------------------------
    info = NativeColorBlock(default="#3b82f6", help_text=_("Info colour"))
    info_content = NativeColorBlock(default="#ffffff", help_text=_("Content on info"))
    success = NativeColorBlock(default="#2DD4BF", help_text=_("Success colour"))
    success_content = NativeColorBlock(
        default="#00332a",
        help_text=_("Content on success"),
    )
    warning = NativeColorBlock(default="#F59E0B", help_text=_("Warning colour"))
    warning_content = NativeColorBlock(
        default="#3d2600",
        help_text=_("Content on warning"),
    )
    error = NativeColorBlock(default="#EF4444", help_text=_("Error colour"))
    error_content = NativeColorBlock(default="#ffffff", help_text=_("Content on error"))

    class Meta:
        icon = "palette"
        group = _("Color Palette")
        collapsed = True


class ColorSchemesBlock(blocks.StructBlock):
    light = ColorPaletteBlock(label=_("Light"), default=LIGHT_MODE_DEFAULT_COLORS)
    dark = ColorPaletteBlock(label=_("Dark"), default=DARK_MODE_DEFAULT_COLORS)

    class Meta:
        icon = "palette"
        group = _("Color Schemes")
        collapsed = True


class ColorSchemesStreamBlock(blocks.StreamBlock):
    color_schemes = ColorSchemesBlock()

    class Meta:
        icon = "palette"
        group = _("Color Schemes")
        collapsed = True
        max_num = 1
        min_num = 1


class PaletteColorInputWidget(ColorInputWidget):
    """Colour picker prepopulated with swatches from SiteDesignSettings."""

    template_name = "wagtailadmin/widgets/color_picker.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        palette_colors = self._load_palette()
        grouped = []
        for group_name, keys in COLOR_GROUPS:
            swatches = []
            for key in keys:
                hex_val = palette_colors.get(key, "")
                if hex_val:
                    swatches.append((key, COLOR_LABELS.get(key, key), hex_val))
            if swatches:
                grouped.append((group_name, swatches))
        context["palette_groups"] = grouped
        return context

    @staticmethod
    def _load_palette():
        try:
            SiteDesignSettings = apps.get_model("core", "SiteDesignSettings")
            ds = SiteDesignSettings.load()
            cp = ds.color_palette
            return {k: cp.get(k, "") for k in COLOR_LABELS if cp.get(k)}
        except Exception:  # noqa: BLE001
            logging.warning("Could not load palette colors for widget", exc_info=True)
            return {}


class PaletteColorPanel(FieldPanel):
    """FieldPanel that uses the palette-aware color picker widget."""

    def get_form_options(self):
        opts = super().get_form_options()
        opts["widgets"] = {self.field_name: PaletteColorInputWidget()}
        return opts


# --- BACKGROUND BLOCKS ---


class FlatBackgroundBlock(blocks.StructBlock):
    color = NativeColorBlock(default="#FFFFFF", help_text=_("Background colour"))

    class Meta:
        group = _("Flat Colour")
        icon = "sliders"
        collapsed = True


class GradientStopBlock(blocks.StructBlock):
    color = NativeColorBlock(default="#FFFFFF", help_text=_("Background colour"))
    position = blocks.FloatBlock(default=0.0, min_value=0.0, max_value=1.0, step=0.1)
    opacity = blocks.FloatBlock(default=1.0, min_value=0.0, max_value=1.0, step=0.1)

    class Meta:
        group = _("Gradient Stop")
        icon = "sliders"
        collapsed = True


class GradientBackgroundBlock(blocks.StructBlock):
    colors = blocks.ListBlock(GradientStopBlock(), required=True)
    direction = blocks.ChoiceBlock(
        choices=GradientDirections.choices,
        default=GradientDirections.TOP_TO_BOTTOM,
    )

    class Meta:
        group = _("Gradient")
        icon = "resubmit"
        collapsed = True


class ImageBackgroundBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True)
    opacity = blocks.FloatBlock(default=1.0, min_value=0.0, max_value=1.0, step=0.1)

    class Meta:
        group = _("Image")
        icon = "image"
        collapsed = True


class GradientImageBackgroundBlock(blocks.StructBlock):
    image = ImageBackgroundBlock(required=True)
    gradient = GradientBackgroundBlock(required=True, label=_("Gradient"))
    opacity = blocks.FloatBlock(default=1.0, min_value=0.0, max_value=1.0, step=0.1)

    class Meta:
        group = _("Gradient + Image")
        icon = "order"
        collapsed = True


class BackgroundStreamBlock(blocks.StreamBlock):
    flat = FlatBackgroundBlock()
    gradient = GradientBackgroundBlock()
    image = ImageBackgroundBlock()
    gradient_image = GradientImageBackgroundBlock()

    class Meta:
        group = _("Background")
        max_num = 1  # prevent an admin from adding dozens of backgrounds


# -- FONT BLOCKS ---


class FontBlock(blocks.StructBlock):
    """
    A block for defining a custom font with link and family name.
    Used in SiteDesignSettings to allow admins to add fonts.
    """

    font_family = blocks.CharBlock(
        required=True,
        max_length=256,
        help_text=_("CSS font-family value, e.g. 'ABeeZee', sans-serif"),
    )
    label = blocks.CharBlock(
        required=True,
        max_length=128,
        help_text=_("Display label for this font, e.g. ABeeZee"),
    )

    class Meta:
        icon = "pilcrow"
        group = _("Font")
        collapsed = True


class TypographyBlock(blocks.StructBlock):
    """
    Typography settings for the site.  Admins can choose heading / body font
    families, add custom font URLs, and set a base font size.
    """

    font_family_heading = blocks.CharBlock(
        default='"Handjet", monospace',
        max_length=256,
        help_text=_('Font family for headings, e.g. "Handjet", monospace'),
    )
    font_family_subheading = blocks.CharBlock(
        default='"Space Mono", monospace',
        max_length=256,
        help_text=_(
            'Font family for subheadings, e.g."Space Mono", monospace',
        ),
    )
    font_family_body = blocks.CharBlock(
        default='"Atkinson Hyperlegible", sans-serif',
        max_length=256,
        help_text=_(
            'Font family for body text, e.g. "Atkinson Hyperlegible", sans-serif',
        ),
    )
    font_url = blocks.ListBlock(
        blocks.URLBlock(required=True, help_text=_("URL to a font stylesheet")),
        required=False,
        label=_("Font URLs"),
        help_text=_("CSS URLs for custom fonts (Bunny Fonts / Google Fonts)"),
    )
    custom_fonts = blocks.ListBlock(
        FontBlock(),
        label=_("Custom Fonts"),
        help_text=_("Additional fonts to include in the site"),
        required=False,
    )
    base_font_size = blocks.IntegerBlock(
        default=16,
        help_text=_("Base font size in pixels (used for scaling)"),
    )

    class Meta:
        icon = "title"
        group = _("Typography")
        collapsed = True

    @property
    def font_families(self):
        """
        Return a list of all font-family values from the custom fonts, in the
        order they were defined.  This is used to populate font-family choices
        in other blocks.
        """
        families = [
            self.get("font_family_heading"),
            self.get("font_family_subheading"),
            self.get("font_family_body"),
        ]

        custom_fonts = self.get("custom_fonts", [])

        families.extend(
            font.get("font_family") for font in custom_fonts if font.get("font_family")
        )

        # Remove duplicates while preserving order
        return list(dict.fromkeys(filter(None, families)))


class TypographyStreamBlock(blocks.StreamBlock):
    typography = TypographyBlock()

    class Meta:
        group = _("Typography")
        collapsed = True
        max_num = 1


class FontFamilyChoiceBlock(blocks.ChoiceBlock):
    """
    A ChoiceBlock that populates its choices from the font families defined in
    the TypographyBlock of SiteDesignSettings.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("choices", self.get_choices_lazy)
        super().__init__(**kwargs)

    @staticmethod
    def get_choices_lazy():
        try:
            SiteDesignSettings = apps.get_model("core", "SiteDesignSettings")
            ds = SiteDesignSettings.load()
            if not ds:
                return []
            families = [
                ds.typography.get("font_family_heading", ""),
                ds.typography.get("font_family_subheading", ""),
                ds.typography.get("font_family_body", ""),
            ]
            custom_fonts = ds.typography.get("custom_fonts", []) or []
            families.extend(
                font.get("font_family")
                for font in custom_fonts
                if font.get("font_family")
            )
            seen = list(dict.fromkeys(filter(None, families)))
            return [(f, f) for f in seen]
        except Exception:  # noqa: BLE001
            return []


class FontWeightChoiceBlock(blocks.ChoiceBlock):
    """
    A ChoiceBlock for font weights.
    """

    choices = FontWeights.choices
    default = FontWeights.NORMAL


class FontStyleChoiceBlock(blocks.StructBlock):
    """
    A StructBlock for font styles (normal, italic, oblique).
    """

    choices = FontStyles.choices
    default = FontStyles.NORMAL


class TextAlignChoiceBlock(blocks.ChoiceBlock):
    """
    A ChoiceBlock for text alignment.
    """

    choices = TextAlignment.choices
    default = TextAlignment.LEFT


class FontStyleBlock(blocks.StructBlock):
    """
    A block for defining font styles (e.g. for a heading), with per-mode
    theming options.
    """

    font_family = FontFamilyChoiceBlock(
        required=False,
        help_text=_("Font family"),
    )
    font_size = blocks.IntegerBlock(
        required=False,
        help_text=_("Font size in pixels"),
    )
    font_weight = FontWeightChoiceBlock(
        required=False,
        help_text=_("Font weight"),
    )
    font_style = FontStyleChoiceBlock(
        required=False,
        help_text=_("Font style"),
    )
    text_align = TextAlignChoiceBlock(
        required=False,
        help_text=_("Text alignment"),
    )
    underline = blocks.BooleanBlock(
        required=False,
        help_text=_("Underline text?"),
    )


# -- THEMED BLOCKS ---


class BorderBlock(blocks.StructBlock):
    """
    A block for defining border styles, with per-mode theming options.
    """

    width = blocks.CharBlock(
        default="1px",
        help_text=_("Border width (e.g. '1px', '0.5rem')"),
    )
    style = blocks.ChoiceBlock(
        choices=BorderStyles.choices,
        default=BorderStyles.SOLID,
        help_text=_("Border style"),
    )
    sides = blocks.MultipleChoiceBlock(
        choices=Sides.choices,
        default=[Sides.LEFT, Sides.RIGHT, Sides.TOP, Sides.BOTTOM],
        help_text=_("Sides to apply the border to"),
    )
    color = NativeColorBlock(
        default="#000000",
        help_text=_("Border color"),
    )
    radius = blocks.IntegerBlock(
        default=0,
        help_text=_("Border radius in pixels"),
    )

    class Meta:
        icon = "minus"
        group = _("Border")
        collapsed = True


class ThemeColorsBlock(blocks.StructBlock):
    """
    Reusable color configuration block.
    """

    background = BackgroundStreamBlock(
        required=False,
        label=_("Background"),
    )

    text_color = NativeColorBlock(
        required=False,
        help_text=_("Text color"),
    )

    border = BorderBlock(required=False, label=_("Border"))

    class Meta:
        icon = "view"
        collapsed = True
        group = _("Colors")


class BlockTheme(blocks.StructBlock):
    """
    Theme configuration for a single color mode.
    """

    mode = blocks.ChoiceBlock(
        choices=ColorScheme.choices,
        default=ColorScheme.LIGHT,
    )
    default = ThemeColorsBlock(label=_("Default theme colors"), required=True)
    interactive = ThemeColorsBlock(
        label=_("Theme colors after interaction (e.g. hover)"),
        required=False,
    )

    class Meta:
        icon = "sliders"
        collapsed = True
        group = _("Theme")


class ThemesStreamBlock(blocks.StreamBlock):
    """
    A StreamBlock for themes.
    """

    themes = blocks.ListBlock(BlockTheme())

    class Meta:
        icon = "sliders"
        group = _("Themes")
        collapsed = True
        min_num = 1
        max_num = 2

    def clean(self, value, *args, **kwargs):
        # Enforce unique modes
        modes = [theme["mode"] for theme in value if theme]
        if len(modes) != len(set(modes)):
            msg = "Color modes must be unique."
            raise ValidationError(msg, code="unique_color_modes")

        return super().clean(value, *args, **kwargs)


class ThemedBlock(blocks.StructBlock):
    """
    A block with per-mode theming options.
    """

    themes = blocks.ListBlock(BlockTheme())

    class Meta:
        abstract = True


class ThemedTypographyBlock(ThemedBlock):
    """
    A themed block for typography settings, allowing different font styles per
    color mode.
    """

    typography = FontStyleBlock(label=_("Typography"), required=False)

    class Meta:
        icon = "title"
        group = _("Themed Typography")
        collapsed = True
