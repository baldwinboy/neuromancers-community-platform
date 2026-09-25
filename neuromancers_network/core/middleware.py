"""Project middleware.

``LocalizationMiddleware`` runs immediately after Django's ``LocaleMiddleware``
and restricts the active locale to the admin-curated set from
:class:`~neuromancers_network.core.models.LocalizationSettings`.
"""

from __future__ import annotations

from django.conf import settings
from django.utils import translation
from django.utils.translation import get_language_from_path
from django.utils.translation import get_language_from_request

from .i18n import available_language_choices
from .i18n import get_localization


class LocalizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        data = get_localization()
        choices = available_language_choices()
        offered = [code for code, _name in choices]
        request.localization = data
        request.available_languages = choices

        if data.get("enabled", True) and offered:
            language = self._select_language(request, data, offered)
            if language:
                translation.activate(language)
                request.LANGUAGE_CODE = language

        return self.get_response(request)

    @staticmethod
    def _explicit_language(request, offered):
        """A language chosen via cookie or URL prefix (not browser detection)."""
        cookie = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if cookie and cookie.split("-")[0] in offered:
            return cookie.split("-")[0]
        path_code = get_language_from_path(request.path_info)
        if path_code and path_code.split("-")[0] in offered:
            return path_code.split("-")[0]
        return None

    def _select_language(self, request, data, offered):
        default = data["default_language"]
        if default not in offered:
            default = sorted(offered)[0]
        if data.get("force_default_language"):
            return default

        explicit = self._explicit_language(request, offered)
        if explicit:
            return explicit

        if data.get("detect_browser_language", True):
            detected = get_language_from_request(request, check_path=False) or ""
            code = detected.split("-")[0]
            if code in offered:
                return code
        return default
