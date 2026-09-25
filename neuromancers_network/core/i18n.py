"""Runtime localization helpers driven by :class:`LocalizationSettings`.

The admin-curated offered languages are read through a short-lived cache so the
middleware and templates can call these helpers freely. The cache is busted by
``core.signals`` whenever the settings row (or its languages) changes.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError

logger = logging.getLogger(__name__)

CACHE_KEY = "neuromancers_network.localization"
CACHE_TTL = 300


def _code_name_map():
    """Return ``{code: name}`` for the code-level supported languages."""
    return dict(getattr(settings, "LANGUAGES", []))


def _defaults():
    supported = _code_name_map()
    default = getattr(settings, "LANGUAGE_CODE", "en").split("-")[0]
    return {
        "enabled": True,
        "default_language": default if default in supported else "en",
        "languages": list(supported),
        "show_language_switcher": True,
        "language_switcher_style": "dropdown",
        "detect_browser_language": True,
        "force_default_language": False,
        "display_currency": "GBP",
        "currency_exchange_enabled": True,
        "exchange_rate_source": "stripe",
        "manual_exchange_rates": {},
    }


def _load():
    """Read the current settings row into a plain dict, or ``None``."""
    from .models import LocalizationSettings  # noqa: PLC0415

    try:
        obj = LocalizationSettings.objects.first()
    except DatabaseError:
        logger.debug("Could not load LocalizationSettings", exc_info=True)
        return None
    if obj is None:
        return None
    return {
        "enabled": obj.enabled,
        "default_language": obj.default_language,
        "languages": list(obj.languages.values_list("code", flat=True)),
        "show_language_switcher": obj.show_language_switcher,
        "language_switcher_style": obj.language_switcher_style,
        "detect_browser_language": obj.detect_browser_language,
        "force_default_language": obj.force_default_language,
        "display_currency": obj.display_currency,
        "currency_exchange_enabled": obj.currency_exchange_enabled,
        "exchange_rate_source": obj.exchange_rate_source,
        "manual_exchange_rates": obj.manual_exchange_rates or {},
    }


def get_localization() -> dict:
    """Return the cached localization configuration (falling back to defaults)."""
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    data = _load() or _defaults()
    cache.set(CACHE_KEY, data, CACHE_TTL)
    return data


def bust_localization_cache() -> None:
    """Drop the cached configuration (called on settings save/delete)."""
    cache.delete(CACHE_KEY)


def available_language_choices() -> list[tuple[str, str]]:
    """Return ``(code, name)`` for the languages the admin offers."""
    data = get_localization()
    names = _code_name_map()
    offered = data.get("languages") or list(names)
    if not data.get("enabled", True):
        offered = [data["default_language"]]
    return [(code, names.get(code, code)) for code in offered if code in names]


def runtime_languages() -> list[tuple[str, str]]:
    """Languages the language switcher should offer."""
    data = get_localization()
    names = _code_name_map()
    if not data.get("show_language_switcher", True):
        default = data["default_language"]
        return [(default, names.get(default, default))]
    return available_language_choices()


def runtime_content_languages() -> list[str]:
    """Language codes offered for translated content pages."""
    data = get_localization()
    if not data.get("enabled", True) or data.get("force_default_language"):
        return [data["default_language"]]
    return [code for code, _name in available_language_choices()] or [
        data["default_language"],
    ]


def active_currency() -> str:
    """The display currency code configured by the admin."""
    return get_localization().get("display_currency", "GBP")
