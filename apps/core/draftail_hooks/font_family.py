import json

from django.utils.html import format_html
from django.utils.safestring import mark_safe


def load_font_family_css():
    """
    Load the CSS for custom font families.
    """
    font_families = []

    try:
        from wagtail.models import Site

        from apps.core.models import WebDesignSettings

        site = Site.objects.filter(is_default_site=True).first()
        if site:
            settings = WebDesignSettings.load(request_or_site=site)
            if settings:
                font_families = settings.get_font_links()
    except Exception:
        pass

    font_import = "\n".join([f"@import url({link});" for link in font_families])
    return f"<style>{font_import}</style>" if font_import else ""


def load_bootstrap_icons_css():
    """
    Load the CSS for Bootstrap Icons.
    """
    cdn_main = "https://cdn.jsdelivr.net/npm/"
    package = "bootstrap-icons@1.13.1/font/bootstrap-icons.min.css"
    link = f"{cdn_main}{package}"
    return format_html('<link rel="stylesheet" href="{}">', link)


def get_font_json_list():
    """
    Get the list of custom fonts in JSON format for use in the Draftail editor.
    """
    font_families = []

    try:
        from wagtail.models import Site

        from apps.core.models import WebDesignSettings

        site = Site.objects.filter(is_default_site=True).first()
        if site:
            settings = WebDesignSettings.load(request_or_site=site)
            if settings:
                font_families = settings.get_font_json_list()
    except Exception:
        pass

    return font_families


def load_font_family_json():
    font_families = get_font_json_list()

    customFontStyleMap = {
        font["type"]: {"fontFamily": font["style"]["fontFamily"]}
        for font in font_families
    }

    # Pass the font family options and style map to the editor via a window JS variable
    # Use mark_safe since json.dumps output is safe for script context

    fonts_json = json.dumps(font_families).replace("</", r"<\/")
    style_map_json = json.dumps(customFontStyleMap).replace("</", r"<\/")
    return mark_safe(
        "<script type='text/javascript'>\n\t"
        "window.customFontFamilies = {};\n\t"
        "window.customFontStyleMap = {};\n"
        "</script>\n".format(fonts_json, style_map_json)
    )
