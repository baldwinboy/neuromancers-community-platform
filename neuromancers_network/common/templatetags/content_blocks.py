from __future__ import annotations

from uuid import uuid4

from django import template
from django.apps import apps
from django.template.defaultfilters import slugify
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from wagtailtraverse import traverse_value

from neuromancers_network.core.models import ContentSettings

register = template.Library()

WIDTH_CLASS_MAP = {
    "auto": "w-auto max-w-none",
    "narrow": "w-full max-w-xl",
    "medium": "w-full max-w-3xl",
    "wide": "w-full max-w-5xl",
    "widest": "w-full max-w-7xl",
    "screen": "w-full max-w-none",
}

HEIGHT_CLASS_MAP = {
    "auto": "h-auto",
    "narrow": "min-h-32",
    "medium": "min-h-48",
    "wide": "min-h-64",
    "widest": "min-h-80",
    "screen": "min-h-screen",
}

JUSTIFY_CLASS_MAP = {
    "center": "justify-center",
    "flex-start": "justify-start",
    "flex-end": "justify-end",
    "space-between": "justify-between",
    "space-around": "justify-around",
    "space-evenly": "justify-evenly",
}

ALIGN_CLASS_MAP = {
    "center": "items-center",
    "flex-start": "items-start",
    "flex-end": "items-end",
    "stretch": "items-stretch",
}


def _site_from_request(request):
    return getattr(request, "site", None)


def _get_content_settings(request):
    site = _site_from_request(request)
    if site is not None:
        return ContentSettings.for_site(site)
    return ContentSettings.load()


def _as_mapping(value):
    return value if hasattr(value, "get") else {}


def _get_root_struct(value):
    """
    Extract the root StructValue from a BoundBlock or StreamValue.
    If value is already a dict-like object, return it directly.
    """
    if hasattr(value, "get") and not hasattr(value, "block"):
        return value
    # Traverse to the first block (the root) and return its value
    for _path, bound_block in traverse_value(value):
        return bound_block.value
    return None


def _pick_mode_value(items, preferred_modes):
    """Pick a theme item from a list by matching its 'mode' against preferred_modes."""
    if not items:
        return None
    for mode in preferred_modes:
        for item in items:
            if item.get("mode") == mode:
                return item
    return items[0]


def _preferred_modes(request):
    theme_name = ""
    if request is not None:
        theme_name = request.COOKIES.get("theme", "")
    if "dark" in theme_name:
        return ["dark", "light"]
    return ["light", "dark"]


def _theme_source(value, request):
    """
    Return the list of theme definitions from the block.
    Falls back to ContentSettings.default_theme if the block has no themes.
    """
    root = _get_root_struct(value)
    themes = root.get("themes", []) if root else []
    if themes:
        return themes
    return list(_get_content_settings(request).default_theme or [])


def _background_styles(background_stream, preferred_modes):
    """Generate CSS for the first background block in a StreamValue."""
    if not background_stream:
        return []
    # background_stream is a StreamValue (list-like of BoundBlock)
    background = background_stream[0] if background_stream else None
    if not background:
        return []

    block_type = background.block_type
    block_value = background.value
    if not block_type or block_value is None:
        return []

    if block_type == "flat":
        return [f"background-color: {block_value.get('color')}"]
    if block_type == "gradient":
        return [
            "background-image: linear-gradient("
            f"{block_value.get('direction', 'to bottom')}, "
            f"{block_value.get('start_color')}, {block_value.get('end_color')})",
        ]
    if block_type == "image":
        image = block_value.get("image")
        if image:
            return [
                f"background-image: url('{image.file.url}')",
                "background-position: center",
                "background-repeat: no-repeat",
                "background-size: cover",
            ]
    if block_type == "gradient_image":
        image = block_value.get("image")
        gradient = _as_mapping(block_value.get("gradient"))
        if image:
            return [
                "background-image: linear-gradient("
                f"{gradient.get('direction', 'to bottom')}, "
                f"{gradient.get('start_color')}, {gradient.get('end_color')}), "
                f"url('{image.file.url}')",
                "background-position: center",
                "background-repeat: no-repeat",
                "background-size: cover",
            ]
    return []


def _border_styles(border):
    border = _as_mapping(border)
    if not border:
        return []

    width = border.get("width", "1px")
    style = border.get("style", "solid")
    color = border.get("color")
    radius = border.get("radius")
    sides = border.get("sides") or ["top", "right", "bottom", "left"]

    rules = []
    if color:
        for side in sides:
            rules.append(f"border-{side}: {width} {style} {color}")
    if radius not in (None, ""):
        rules.append(f"border-radius: {radius}px")
    return rules


def _theme_styles(value, request):
    root = _get_root_struct(value)
    if not root:
        return []

    preferred_modes = _preferred_modes(request)
    theme_entry = _pick_mode_value(_theme_source(value, request), preferred_modes)
    if not theme_entry:
        return []

    default_theme = _as_mapping(theme_entry.get("default"))
    rules = _background_styles(default_theme.get("background") or [], preferred_modes)

    text_color = default_theme.get("text_color")
    if text_color:
        rules.append(f"color: {text_color}")

    rules.extend(_border_styles(default_theme.get("border")))
    return rules


def _typography_styles(value):
    root = _get_root_struct(value)
    typography = _as_mapping(root.get("typography")) if root else {}
    if not typography:
        return []

    font_family = typography.get("font_family")
    font_size = typography.get("font_size")
    font_weight = typography.get("font_weight")
    font_style = typography.get("font_style")
    text_align = typography.get("text_align")
    underline = typography.get("underline")

    rules = []
    if font_family:
        rules.append(f"font-family: {font_family}")
    if font_size:
        rules.append(f"font-size: {font_size}px")
        rules.append(f"line-height: {round(font_size * 1.35, 2)}px")
    if font_weight:
        rules.append(f"font-weight: {font_weight}")
    if font_style:
        rules.append(f"font-style: {font_style}")
    if text_align:
        rules.append(f"text-align: {text_align}")
    if underline:
        rules.append("text-decoration: underline")
    return rules


def _dimension_styles(value):
    root = _get_root_struct(value)
    if not root:
        return []

    rules = []
    fixed_width = root.get("fixed_width")
    fixed_height = root.get("fixed_height")
    width = root.get("width")
    height = root.get("height")

    if fixed_width:
        rules.append(f"width: min(100%, {fixed_width}px)")
    elif width == "screen" or width != "auto":
        rules.append("width: 100%")

    if fixed_height:
        rules.append(f"height: {fixed_height}px")
    elif height == "screen":
        rules.append("min-height: 100vh")
    return rules


def _resolve_candidate(context, model_label):
    app_label, model_name = model_label.split(".", 1)
    model = apps.get_model(app_label, model_name)
    if model is None:
        return None

    request = context.get("request")
    page = context.get("page")
    object_ = context.get("object")
    user = context.get("user") or getattr(request, "user", None)

    context_objects = context.get("context_objects", {})
    explicit = context_objects.get(model_label)

    candidates = [
        explicit,
        object_,
        page,
        getattr(page, "specific", None),
        user,
    ]

    if user is not None:
        candidates.append(getattr(user, "profile", None))

    for candidate in candidates:
        if candidate is not None and isinstance(candidate, model):
            return candidate

    return None


@register.simple_tag(takes_context=True)
def block_visible(context, value):
    # Visibility logic is currently disabled (always True)
    return True


@register.simple_tag(takes_context=True)
def block_style(context, value):
    request = context.get("request")
    rules = []
    rules.extend(_theme_styles(value, request))
    rules.extend(_typography_styles(value))
    rules.extend(_dimension_styles(value))
    return "; ".join(rule for rule in rules if rule)


@register.simple_tag
def border_style(border):
    return "; ".join(rule for rule in _border_styles(border) if rule)


@register.simple_tag
def block_size_classes(value, centered=True):
    classes = []
    width = value.get("width", "auto")
    height = value.get("height", "auto")

    classes.append(WIDTH_CLASS_MAP.get(width, WIDTH_CLASS_MAP["auto"]))
    classes.append(HEIGHT_CLASS_MAP.get(height, HEIGHT_CLASS_MAP["auto"]))
    if centered and width != "screen":
        classes.append("mx-auto")
    return " ".join(filter(None, classes))


@register.simple_tag
def justify_class(choice):
    return JUSTIFY_CLASS_MAP.get(choice, "")


@register.simple_tag
def align_class(choice):
    return ALIGN_CLASS_MAP.get(choice, "")


@register.simple_tag
def link_url(link_value):
    if hasattr(link_value, "get_url"):
        return link_value.get_url() or ""
    return ""


@register.simple_tag
def link_target_attrs(link_value):
    if not link_value or not link_value.get("new_window"):
        return ""
    return mark_safe('target="_blank" rel="noreferrer noopener"')


def _resolve_attribute(candidate, model_field):
    parts = model_field.split(".")
    current = candidate
    for part in parts:
        if current is None:
            return ""
        current = getattr(current, part, None)
        if callable(current):
            current = current()
    return current if current is not None else ""


@register.simple_tag(takes_context=True)
def attribute_value(context, value):
    model_label = value.get("model")
    model_field = value.get("model_field")
    if not model_label or not model_field:
        return ""

    try:
        candidate = _resolve_candidate(context, model_label)
    except LookupError, ValueError:
        return ""

    if candidate is None:
        return ""

    return _resolve_attribute(candidate, model_field)


@register.simple_tag
def block_id(prefix="block"):
    return f"{slugify(prefix) or 'block'}-{uuid4().hex[:8]}"


@register.filter
def escape_attr(value):
    return conditional_escape(value)
