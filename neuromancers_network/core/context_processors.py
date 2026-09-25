"""Template context processors."""

from __future__ import annotations

from .i18n import available_language_choices
from .i18n import get_localization


def localization(request):
    """Expose the localization configuration to templates."""
    data = getattr(request, "localization", None) or get_localization()
    languages = getattr(request, "available_languages", None)
    if languages is None:
        languages = available_language_choices()
    return {
        "localization": data,
        "available_languages": languages,
        "show_language_switcher": data.get("show_language_switcher", True),
    }


def daisie_themes(request):
    """Expose the non-default DaisyUI theme so the base template can emit its
    CSS, which is what makes the header menu's light/dark toggle work."""
    try:
        from wagtail_daisIE.models import DaisyUITheme  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return {"daisyui_alternate_theme": None}

    try:
        themes = list(DaisyUITheme.objects.order_by("name"))
    except Exception:  # noqa: BLE001
        return {"daisyui_alternate_theme": None}

    if not themes:
        return {"daisyui_alternate_theme": None}

    default = next((theme for theme in themes if theme.default), None)
    alternate = next((theme for theme in themes if theme is not default), None)
    return {"daisyui_alternate_theme": alternate}
