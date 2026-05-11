from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import render
from wagtail.models import Site

from neuromancers_network.core.models import SiteLockSettings


class SiteLockMiddleware:
    """Enforce site lock mode for non-staff users until they unlock via password."""

    LOCK_PATH = "/site-lock/"
    SESSION_KEY = "site_lock_unlocked"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_bypass(request):
            return self.get_response(request)

        lock_settings = self._get_lock_settings(request)
        if lock_settings is None or lock_settings.is_public:
            return self.get_response(request)

        if request.user.is_authenticated and request.user.is_staff:
            return self.get_response(request)

        if request.session.get(self.SESSION_KEY, False):
            return self.get_response(request)

        if request.path == self.LOCK_PATH:
            return self._handle_lock_screen(request, lock_settings)

        query = urlencode({"next": request.get_full_path()})
        return HttpResponseRedirect(f"{self.LOCK_PATH}?{query}")

    def _should_bypass(self, request) -> bool:
        path = request.path
        always_allow_prefixes = (
            "/health",
            "/static/",
            "/media/",
            "/api/",
            "/cms/",
            "/documents/",
            "/__debug__/",
            f"/{settings.ADMIN_URL}"
            if not settings.ADMIN_URL.startswith("/") else settings.ADMIN_URL,
            "/login",
            "/signup",
            "/logout",
            "/password",
            "/accounts/",
        )
        return path.startswith(always_allow_prefixes)

    def _get_lock_settings(self, request):
        try:
            site = Site.find_for_request(request)
            if site is None:
                return None
            return SiteLockSettings.for_site(site)
        except Exception:
            # During initial migrate/check when tables are not ready yet.
            return None

    def _is_password_valid(self, lock_settings,
                           submitted_password: str) -> bool:
        if lock_settings.password_hash:
            return check_password(submitted_password,
                                  lock_settings.password_hash)
        return submitted_password == settings.SITE_LOCK_DEFAULT_PASSWORD

    def _handle_lock_screen(self, request, lock_settings):
        next_url = request.POST.get("next") or request.GET.get("next") or "/"
        error = ""

        if request.method == "POST":
            submitted_password = request.POST.get("password", "")
            if self._is_password_valid(lock_settings, submitted_password):
                request.session[self.SESSION_KEY] = True
                return HttpResponseRedirect(next_url)
            error = "Incorrect password."

        return render(
            request,
            "pages/site_lock.html",
            {
                "maintenance_message": lock_settings.maintenance_message,
                "error": error,
                "next": next_url,
            },
            status=423,
        )


class HealthCheckMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in {"/health", "/health/"}:
            database_status = "ok"
            redis_status = "ok"
            status_code = 200

            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            except OperationalError:
                database_status = "error"
                status_code = 503

            try:
                cache.set("healthcheck", "ok", 5)
                if cache.get("healthcheck") != "ok":
                    raise RuntimeError("Redis cache round-trip failed")
            except Exception:
                redis_status = "error"
                status_code = 503

            return JsonResponse(
                {
                    "status": "ok" if status_code == 200 else "error",
                    "database": database_status,
                    "redis": redis_status,
                },
                status=status_code,
            )
        return self.get_response(request)
