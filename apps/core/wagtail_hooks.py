import json

from django.templatetags.static import static
from django.urls import path, reverse
from django.utils.html import format_html, json_script, smart_urlquote
from django.utils.safestring import mark_safe
from draftjs_exporter.dom import DOM
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    InlineEntityElementHandler,
    InlineStyleElementHandler,
)
from wagtail.admin.rich_text.editors.draftail.features import (
    ControlFeature,
    EntityFeature,
    InlineStyleFeature,
)
from wagtail.admin.ui.components import Component

from .draftail_hooks.color import get_color_json_list, load_color_json
from .draftail_hooks.font_family import (
    get_font_json_list,
    load_bootstrap_icons_css,
    load_font_family_css,
    load_font_family_json,
)


@hooks.register("register_icons")
def register_icons(icons):
    return icons + [
        "wagtailadmin/icons/stripe.svg",
        "wagtailadmin/icons/whereby.svg",
        "wagtailadmin/icons/filter.svg",
        "wagtailadmin/icons/emoji.svg",
        "wagtailadmin/icons/fonts.svg",
    ]


@hooks.register("insert_global_admin_css")
def global_admin_css():
    font_family_css = load_font_family_css()
    bootstrap_icons_css = load_bootstrap_icons_css()
    return (
        bootstrap_icons_css
        + font_family_css
        + format_html(
            '<link rel="stylesheet" href="{}">' '<link rel="stylesheet" href="{}">',
            static("css/emoji_picker.css"),
            static("css/color_picker.css"),
        )
        + format_html(
            '<link rel="stylesheet" href="{}">' '<link rel="stylesheet" href="{}">',
            static("css/_fonts.css"),
            static("css/common.css"),
        )
    )


@hooks.register("insert_global_admin_js")
def global_admin_js():
    font_family_json = load_font_family_json()
    color_json = load_color_json()
    return (
        font_family_json
        + color_json
        + format_html(
            '<script src="{}"></script>' '<script src="{}"></script>',
            static("js/emoji_picker.js"),
            static("js/color_picker.js"),
        )
    )


# Platform Guide hooks
@hooks.register("register_admin_urls")
def register_platform_guide_url():
    from apps.core.views import platform_guide_view

    return [
        path("platform-guide/", platform_guide_view, name="platform_guide"),
        path(
            "platform-guide/<slug:page_slug>/",
            platform_guide_view,
            name="platform_guide_page",
        ),
    ]


@hooks.register("register_help_menu_item")
def register_platform_guide_help_menu_item():
    return MenuItem(
        "Platform Guide",
        reverse("platform_guide"),
        icon_name="help",
        order=100,
    )


@hooks.register("construct_homepage_panels")
def add_platform_guide_panel(_request, panels):
    """Add a prominent Platform Guide button to the Wagtail admin dashboard."""
    panels.append(PlatformGuidePanel())


@hooks.register("register_rich_text_features")
def register_font_family_styling(features):
    """
    Register a custom rich text feature for font family styling,
    allowing content editors to apply specific font families to their text.
    """
    font_families = get_font_json_list()

    for font in font_families:
        style = font["style"]
        type_ = font["type"]
        font_family = style["fontFamily"]

        features.register_editor_plugin(
            "draftail",
            type_,
            InlineStyleFeature(
                {
                    "type": type_,
                    "style": style,
                },
            ),
        )

        # HTML -> Draft.js
        features.register_converter_rule(
            "contentstate",
            type_,
            {
                "from_database_format": {
                    f'span[style="font-family: {font_family};"]': InlineStyleElementHandler(
                        type_
                    ),
                },
                "to_database_format": {
                    "style_map": {
                        type_: {
                            "element": "span",
                            "props": {
                                "style": f"font-family: {font_family};",
                            },
                        }
                    }
                },
            },
        )

        features.default_features.append(type_)

    # Register Control for font family selection in the toolbar
    feature_name = "font-family"

    features.register_editor_plugin(
        "draftail",
        feature_name,
        ControlFeature(
            {
                "type": feature_name,
            },
            js=["js/draftail/font_family.js"],
            css={"all": ("css/draftail/font_family.css",)},
        ),
    )
    features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_font_size_styling(features):
    """
    Register a custom rich text feature for font size styling,
    allowing content editors to apply specific font sizes to their text.
    """
    font_sizes = list(range(1, 401))  # 1 to 400 (covers all presets + arbitrary input)

    for size in font_sizes:
        type_ = f"FONT_SIZE_{size}"

        features.register_editor_plugin(
            "draftail",
            type_,
            InlineStyleFeature(
                {
                    "type": type_,
                    "style": {"fontSize": f"{size}px"},
                },
            ),
        )

        # HTML -> Draft.js
        features.register_converter_rule(
            "contentstate",
            type_,
            {
                "from_database_format": {
                    f'span[style="font-size: {size}px;"]': InlineStyleElementHandler(
                        type_
                    ),
                },
                "to_database_format": {
                    "style_map": {
                        type_: {
                            "element": "span",
                            "props": {
                                "style": f"font-size: {size}px;",
                            },
                        }
                    }
                },
            },
        )

        features.default_features.append(type_)

    # Register Control for font size selection in the toolbar
    feature_name = "font-size"

    features.register_editor_plugin(
        "draftail",
        feature_name,
        ControlFeature(
            {
                "type": feature_name,
            },
            js=["js/draftail/font_size.js"],
            css={"all": ("css/draftail/font_size.css",)},
        ),
    )
    features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_text_color_styling(features):
    """
    Register a custom rich text feature for text color styling,
    allowing content editors to apply specific text colors to their text.
    Colors are loaded from WebDesignSettings.
    """
    colors = get_color_json_list()

    for color in colors:
        type_ = f"TEXT_COLOR_{color['key'].upper()}"
        color_value = color["value"]

        features.register_editor_plugin(
            "draftail",
            type_,
            InlineStyleFeature(
                {
                    "type": type_,
                    "style": {"color": color_value},
                },
            ),
        )

        # HTML -> Draft.js
        features.register_converter_rule(
            "contentstate",
            type_,
            {
                "from_database_format": {
                    f'span[style="color: {color_value};"]': InlineStyleElementHandler(
                        type_
                    ),
                },
                "to_database_format": {
                    "style_map": {
                        type_: {
                            "element": "span",
                            "props": {
                                "style": f"color: {color_value};",
                            },
                        }
                    }
                },
            },
        )

        features.default_features.append(type_)

    # Register Control for text color selection in the toolbar
    feature_name = "text-color"

    features.register_editor_plugin(
        "draftail",
        feature_name,
        ControlFeature(
            {
                "type": feature_name,
            },
            js=["js/draftail/text_color.js"],
            css={"all": ("css/draftail/text_color.css",)},
        ),
    )
    features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_highlight_color_styling(features):
    """
    Register a custom rich text feature for highlight/background color styling,
    allowing content editors to highlight text with specific colors.
    Colors are loaded from WebDesignSettings.
    """
    colors = get_color_json_list()

    for color in colors:
        type_ = f"HIGHLIGHT_COLOR_{color['key'].upper()}"
        color_value = color["value"]

        features.register_editor_plugin(
            "draftail",
            type_,
            InlineStyleFeature(
                {
                    "type": type_,
                    "style": {"backgroundColor": color_value},
                },
            ),
        )

        # HTML -> Draft.js
        features.register_converter_rule(
            "contentstate",
            type_,
            {
                "from_database_format": {
                    f'span[style="background-color: {color_value};"]': InlineStyleElementHandler(
                        type_
                    ),
                },
                "to_database_format": {
                    "style_map": {
                        type_: {
                            "element": "span",
                            "props": {
                                "style": f"background-color: {color_value};",
                            },
                        }
                    }
                },
            },
        )

        features.default_features.append(type_)

    # Register Control for highlight color selection in the toolbar
    feature_name = "highlight-color"

    features.register_editor_plugin(
        "draftail",
        feature_name,
        ControlFeature(
            {
                "type": feature_name,
            },
            js=["js/draftail/highlight_color.js"],
            css={"all": ("css/draftail/highlight_color.css",)},
        ),
    )
    features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_custom_text_color_entity(features):
    """
    Register the CUSTOM_TEXT_COLOR entity type for arbitrary text colors
    picked via the color picker in the text-color control.
    """
    feature_name = "custom-text-color"

    def custom_text_color_entity_decorator(props):
        color = props.get("color", "")
        return DOM.create_element(
            "span",
            {"style": f"color: {color};", "data-entity-type": "CUSTOM_TEXT_COLOR"},
            props["children"],
        )

    class CustomTextColorEntityHandler(InlineEntityElementHandler):
        mutability = "MUTABLE"

        def get_attribute_data(self, attrs):
            style = attrs.get("style", "")
            color = ""
            for part in style.split(";"):
                part = part.strip()
                if part.startswith("color:"):
                    color = part.split(":", 1)[1].strip()
                    break
            return {"color": color}

    features.register_editor_plugin(
        "draftail",
        feature_name,
        EntityFeature(
            {"type": "CUSTOM_TEXT_COLOR", "attributes": ["color"]},
            js=["js/draftail/custom_text_color.js"],
        ),
    )

    features.register_converter_rule(
        "contentstate",
        feature_name,
        {
            "from_database_format": {
                "span[data-entity-type='CUSTOM_TEXT_COLOR']": CustomTextColorEntityHandler(
                    "CUSTOM_TEXT_COLOR"
                ),
            },
            "to_database_format": {
                "entity_decorators": {
                    "CUSTOM_TEXT_COLOR": custom_text_color_entity_decorator
                }
            },
        },
    )

    features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_custom_highlight_color_entity(features):
    """
    Register the CUSTOM_HIGHLIGHT_COLOR entity type for arbitrary highlight colors
    picked via the color picker in the highlight-color control.
    """
    feature_name = "custom-highlight-color"

    def custom_highlight_color_entity_decorator(props):
        color = props.get("color", "")
        return DOM.create_element(
            "span",
            {
                "style": f"background-color: {color};",
                "data-entity-type": "CUSTOM_HIGHLIGHT_COLOR",
            },
            props["children"],
        )

    class CustomHighlightColorEntityHandler(InlineEntityElementHandler):
        mutability = "MUTABLE"

        def get_attribute_data(self, attrs):
            style = attrs.get("style", "")
            color = ""
            for part in style.split(";"):
                part = part.strip()
                if part.startswith("background-color:"):
                    color = part.split(":", 1)[1].strip()
                    break
            return {"color": color}

    features.register_editor_plugin(
        "draftail",
        feature_name,
        EntityFeature(
            {"type": "CUSTOM_HIGHLIGHT_COLOR", "attributes": ["color"]},
            js=["js/draftail/custom_highlight_color.js"],
        ),
    )

    features.register_converter_rule(
        "contentstate",
        feature_name,
        {
            "from_database_format": {
                "span[data-entity-type='CUSTOM_HIGHLIGHT_COLOR']": CustomHighlightColorEntityHandler(
                    "CUSTOM_HIGHLIGHT_COLOR"
                ),
            },
            "to_database_format": {
                "entity_decorators": {
                    "CUSTOM_HIGHLIGHT_COLOR": custom_highlight_color_entity_decorator
                }
            },
        },
    )

    features.default_features.append(feature_name)


class PlatformGuidePanel(Component):
    order = 50
    template_name = "wagtailadmin/panels/platform_guide.html"
