"""Project middleware.

``LocalizationMiddleware`` runs immediately after Django's ``LocaleMiddleware``
and restricts the active locale to the admin-curated set from
:class:`~neuromancers_network.core.models.LocalizationSettings`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseBase
from django.utils import translation
from django.utils.cache import patch_vary_headers
from django.utils.translation import get_language_from_path
from django.utils.translation import get_language_from_request

from .bootstrap_state import current_status
from .i18n import available_language_choices
from .i18n import get_localization

if TYPE_CHECKING:
    from collections.abc import Callable


class LocalizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        data = get_localization()
        choices = available_language_choices()
        offered = [code for code, _name in choices]
        request.localization = data
        request.available_languages = choices

        if not data.get("enabled", True):
            default = data["default_language"]
            if default not in offered and offered:
                default = sorted(offered)[0]
            if default:
                translation.activate(default)
                request.LANGUAGE_CODE = default
        elif offered:
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


class ConsentVaryMiddleware:
    """HTML responses depend on the consent cookie; keep caches correct."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if "text/html" in response.get("Content-Type", ""):
            patch_vary_headers(response, ("Cookie",))
        return response


class BootstrapGateMiddleware:
    """Return 503 until the production bootstrap has completed."""

    EXEMPT_PATHS = frozenset({"/api/health", "/api/ready"})
    EXEMPT_PREFIXES = ("/static/", "/media/")

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponseBase],
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        if not getattr(settings, "BOOTSTRAP_GATE_ENABLED", False):
            return self.get_response(request)
        if self._is_exempt(request.path_info):
            return self.get_response(request)
        if current_status().serving_allowed:
            return self.get_response(request)

        response = HttpResponse(
            "Service temporarily unavailable during deployment.\n",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
        response["Retry-After"] = "30"
        response["Cache-Control"] = "no-store"
        return response

    @classmethod
    def _is_exempt(cls, path: str) -> bool:
        normalized = path.rstrip("/") or "/"
        if normalized in cls.EXEMPT_PATHS:
            return True
        return any(
            path == prefix.rstrip("/") or path.startswith(prefix)
            for prefix in cls.EXEMPT_PREFIXES
        )
