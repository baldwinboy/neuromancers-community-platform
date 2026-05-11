from logging import Logger

from wagtailtraverse import traverse_value

from neuromancers_network.common.blocks.base import LIGHT_MODE_DEFAULT_COLORS

from .models import SiteDesignSettings

logger = Logger(__name__)

DAISY_COLOR_KEYS = [
    "base_100",
    "base_200",
    "base_300",
    "base_content",
    "primary",
    "primary_content",
    "secondary",
    "secondary_content",
    "accent",
    "accent_content",
    "neutral",
    "neutral_content",
    "info",
    "info_content",
    "success",
    "success_content",
    "warning",
    "warning_content",
    "error",
    "error_content",
]


def _extract_struct_from_field(field_value):
    """
    Extract a dict from a Wagtail StreamValue/BoundBlock or return the value itself
    if it's already a dict/list. Returns empty dict if extraction fails.
    """
    if not field_value:
        return {}
    # If it's already dict-like (has .get, no .block), return as is
    if hasattr(field_value, "get") and not hasattr(field_value, "block"):
        return field_value
    # If it's a list (e.g., a list of blocks), we might want the first block's value
    if isinstance(field_value, list):
        # If it's a list of BoundBlocks, extract first block's value
        if field_value and hasattr(field_value[0], "block"):
            for _path, bound_block in traverse_value(field_value):
                return bound_block.value
        return {}
    # For StreamValue or BoundBlock, traverse to get the root value
    try:
        for _path, bound_block in traverse_value(field_value):
            return bound_block.value
    except Exception:
        logger.exception("Failed to extract struct from field %s", field_value)
    return {}


def _normalise_scheme(scheme):
    scheme = scheme or {}
    colors = {
        key: scheme.get(key, LIGHT_MODE_DEFAULT_COLORS[key]) for key in DAISY_COLOR_KEYS
    }
    return {"colors": colors}


def _normalise_font_urls(font_urls):
    if not font_urls:
        return []
    if isinstance(font_urls, str):
        return [font_urls]
    return list(font_urls)


def design_variables(request):
    """Expose site_design with daisyUI-compatible CSS variable values."""
    try:
        ds = SiteDesignSettings.load()
        cp = ds.color_palette or {}
        tp = ds.typography or {}
        bgs = ds.backgrounds  # Keep as StreamValue (iterable of BoundBlock)
    except SiteDesignSettings.DoesNotExist, AttributeError:
        return {"site_design": {}}

    # Extract the struct from color_palette if it's a stream
    cp_struct = _extract_struct_from_field(cp)
    light_scheme = _normalise_scheme(cp_struct.get("light"))
    dark_scheme = _normalise_scheme(cp_struct.get("dark"))

    # typography might also be a stream – extract if needed
    tp_struct = _extract_struct_from_field(tp)

    typography = {
        "font_heading": tp_struct.get("font_family_heading", '"Handjet", monospace'),
        "font_body": tp_struct.get(
            "font_family_body",
            '"Atkinson Hyperlegible", sans-serif',
        ),
        "font_subheading": tp_struct.get(
            "font_family_subheading",
            '"Space Mono", monospace',
        ),
        "font_urls": _normalise_font_urls(tp_struct.get("font_url", [])),
        "base_font_size": tp_struct.get("base_font_size", 16),
        "custom_fonts": tp_struct.get("custom_fonts", []),
    }

    return {
        "site_design": {
            "color_schemes": {
                "light": light_scheme,
                "dark": dark_scheme,
            },
            "typography": typography,
            "backgrounds": bgs,  # Pass through untouched
        },
    }
