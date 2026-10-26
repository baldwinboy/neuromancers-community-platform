"""Template context processors."""

from __future__ import annotations

import logging

from django.db import DatabaseError

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


logger = logging.getLogger(__name__)


def site_scripts(request):
    """Expose audience-matching, consented head/body scripts."""
    from wagtail_daisIE.base_blocks.audience import evaluate_audience  # noqa: PLC0415

    from .consent import consent_allows  # noqa: PLC0415
    from .models import ScriptsSetting  # noqa: PLC0415

    try:
        configured = ScriptsSetting.load(request).scripts
    except DatabaseError:
        logger.exception("Could not load script settings")
        return {"head_scripts": [], "body_scripts": []}

    head_scripts = []
    body_scripts = []
    for block in configured:
        value = block.value
        if not consent_allows(request, value["category"]):
            continue
        if not evaluate_audience(value["audience"], request):
            continue
        target = head_scripts if value["placement"] == "head" else body_scripts
        target.append(value["code"])
    return {"head_scripts": head_scripts, "body_scripts": body_scripts}


def consent_banner(request):
    """Expose the signed consent and admin-authored banner copy."""
    from .consent import consent_needs_update  # noqa: PLC0415
    from .consent import read_consent  # noqa: PLC0415
    from .models import ConsentSettings  # noqa: PLC0415
    from .models import CookieCategory  # noqa: PLC0415

    try:
        settings_obj = ConsentSettings.load(request)
    except DatabaseError:
        logger.exception("Could not load consent settings")
        return {
            "consent": {},
            "consent_needs_update": False,
            "consent_settings": None,
            "consent_categories": [],
        }
    return {
        "consent": read_consent(request),
        "consent_needs_update": consent_needs_update(request, settings_obj),
        "consent_settings": settings_obj,
        "consent_categories": [
            (value, label)
            for value, label in CookieCategory.choices
            if value != CookieCategory.NECESSARY
        ],
    }
