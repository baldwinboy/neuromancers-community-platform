from __future__ import annotations

import re

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.http import HttpResponseRedirect


class SecurityHeadersMiddleware:
    """Apply security headers to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not getattr(settings, "SECURE_HSTS_INCLUDE_SUBDOMAINS", False):
            return response

        if not response.has_header("Strict-Transport-Security"):
            response["Strict-Transport-Security"] = (
                f"max-age={settings.SECURE_HSTS_SECONDS}"
                f"{'; includeSubDomains' if getattr(settings, 'SECURE_HSTS_INCLUDE_SUBDOMAINS', False) else ''}"
                f"{'; preload' if getattr(settings, 'SECURE_HSTS_PRELOAD', False) else ''}"
            )

        if not response.has_header("X-Content-Type-Options"):
            response["X-Content-Type-Options"] = "nosniff"

        if not response.has_header("X-Frame-Options"):
            response["X-Frame-Options"] = "DENY"

        if not response.has_header("Referrer-Policy"):
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if not response.has_header("X-XSS-Protection"):
            response["X-XSS-Protection"] = "0"

        if not response.has_header("Permissions-Policy"):
            response["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=(), interest-cohort=()"
            )

        return response


class ContentSecurityPolicyMiddleware:
    """Apply Content-Security-Policy header."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._directives = self._build_directives()

    def _build_directives(self) -> str:
        CSP = getattr(settings, "CONTENT_SECURITY_POLICY", {})
        directives = []
        for key, values in CSP.items():
            key = re.sub(r"_(?=[a-z])", "-", key).lower()
            if isinstance(values, (list, tuple)):
                directives.append(f"{key} {' '.join(values)}")
            else:
                directives.append(f"{key} {values}")
        return "; ".join(directives)

    def __call__(self, request):
        response = self.get_response(request)
        if self._directives:
            response["Content-Security-Policy"] = self._directives
        return response
