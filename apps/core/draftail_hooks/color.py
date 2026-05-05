"""
Color helpers for Draftail editor.
Loads color definitions from WebDesignSettings and injects them into the admin.
"""

import json

from django.utils.safestring import mark_safe


def get_color_json_list():
    """
    Get the list of colors in JSON format for use in the Draftail editor.
    Returns a list of color objects with type, label, and style.
    """
    color_list = []

    try:
        from wagtail.models import Site

        from apps.core.models import WebDesignSettings

        site = Site.objects.filter(is_default_site=True).first()
        if site:
            settings = WebDesignSettings.load(request_or_site=site)
            if settings:
                color_choices = settings.get_color_choices()
                color_map = settings.get_color_map()

                for choice in color_choices:
                    key = choice[0]
                    label = choice[1]
                    value = color_map.get(key, key)

                    color_list.append(
                        {
                            "type": f"COLOR_{key.upper()}",
                            "label": label,
                            "value": value,
                            "key": key,
                        }
                    )
    except Exception:
        # Fallback to default colors if settings aren't available
        color_list = [
            {
                "type": "COLOR_TRANSPARENT",
                "label": "Transparent",
                "value": "transparent",
                "key": "transparent",
            },
            {
                "type": "COLOR_WHITE",
                "label": "White",
                "value": "hsl(0, 0%, 100%)",
                "key": "white",
            },
            {
                "type": "COLOR_BLACK",
                "label": "Black",
                "value": "hsl(0, 100%, 0.78%)",
                "key": "black",
            },
            {
                "type": "COLOR_ACCENT",
                "label": "Accent",
                "value": "hsl(342.63, 80.85%, 81.57%)",
                "key": "accent",
            },
            {
                "type": "COLOR_LIGHTACCENT",
                "label": "Light Accent",
                "value": "hsl(343.29, 95.89%, 71.37%)",
                "key": "lightAccent",
            },
            {
                "type": "COLOR_DARKACCENT",
                "label": "Dark Accent",
                "value": "hsl(342.11, 40.43%, 27.65%)",
                "key": "darkAccent",
            },
        ]

    return color_list


def load_color_json():
    """
    Load color definitions as a JavaScript script tag for the Draftail admin.
    This injects window.customTextColors and window.customHighlightColors.
    """
    colors = get_color_json_list()

    # Create style maps for text color and highlight color
    text_color_style_map = {
        color["type"].replace("COLOR_", "TEXT_COLOR_"): {"color": color["value"]}
        for color in colors
    }

    highlight_color_style_map = {
        color["type"].replace("COLOR_", "HIGHLIGHT_COLOR_"): {
            "backgroundColor": color["value"]
        }
        for color in colors
    }

    # Transform colors for text color use
    text_colors = [
        {
            "type": color["type"].replace("COLOR_", "TEXT_COLOR_"),
            "label": color["label"],
            "value": color["value"],
            "key": color["key"],
            "style": {"color": color["value"]},
        }
        for color in colors
    ]

    # Transform colors for highlight color use
    highlight_colors = [
        {
            "type": color["type"].replace("COLOR_", "HIGHLIGHT_COLOR_"),
            "label": color["label"],
            "value": color["value"],
            "key": color["key"],
            "style": {"backgroundColor": color["value"]},
        }
        for color in colors
    ]

    # JSON encode and escape for script context
    text_colors_json = json.dumps(text_colors).replace("</", r"<\/")
    highlight_colors_json = json.dumps(highlight_colors).replace("</", r"<\/")
    text_color_style_map_json = json.dumps(text_color_style_map).replace("</", r"<\/")
    highlight_color_style_map_json = json.dumps(highlight_color_style_map).replace(
        "</", r"<\/"
    )

    return mark_safe(
        "<script type='text/javascript'>\n\t"
        f"window.customTextColors = {text_colors_json};\n\t"
        f"window.customHighlightColors = {highlight_colors_json};\n\t"
        f"window.customTextColorStyleMap = {text_color_style_map_json};\n\t"
        f"window.customHighlightColorStyleMap = {highlight_color_style_map_json};\n"
        "</script>\n"
    )
