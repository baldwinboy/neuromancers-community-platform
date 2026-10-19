"""Cookie-consent helpers (a single signed cookie)."""

from __future__ import annotations

from django.core import signing
from django.db import DatabaseError
from django.utils import timezone

COOKIE_NAME = "cookie_consent"
SIGNING_SALT = "core.cookie-consent"
MAX_AGE_SECONDS = 60 * 60 * 24 * 365

NECESSARY = "necessary"
ANALYTICS = "analytics"
MARKETING = "marketing"
CATEGORIES = (NECESSARY, ANALYTICS, MARKETING)


def read_consent(request) -> dict:
    """Return the consent payload, or an empty mapping when absent/invalid."""
    raw = request.COOKIES.get(COOKIE_NAME)
    if not raw:
        return {}
    try:
        return signing.loads(raw, salt=SIGNING_SALT, max_age=MAX_AGE_SECONDS)
    except signing.BadSignature:
        return {}


def consent_allows(request, category: str) -> bool:
    """Necessary scripts always run; others require explicit consent."""
    if category in (NECESSARY, ""):
        return True
    return category in (read_consent(request).get("categories") or [])


def write_consent(response, *, categories, version, secure=False):
    """Persist the visitor's choice in the signed consent cookie."""
    allowed = sorted(
        {category for category in categories if category in (ANALYTICS, MARKETING)},
    )
    payload = {
        "categories": allowed,
        "version": version,
        "timestamp": timezone.now().isoformat(),
    }
    response.set_cookie(
        COOKIE_NAME,
        signing.dumps(payload, salt=SIGNING_SALT),
        max_age=MAX_AGE_SECONDS,
        httponly=False,
        samesite="Lax",
        secure=secure,
    )


def clear_consent(response):
    response.delete_cookie(COOKIE_NAME, samesite="Lax")


def current_policy_version() -> str:
    from .models import ConsentSettings  # noqa: PLC0415

    try:
        return ConsentSettings.load().policy_version or "1"
    except DatabaseError:
        return "1"


def consent_needs_update(request) -> bool:
    """Whether the banner should be shown (absent or stale policy version)."""
    payload = read_consent(request)
    if not payload:
        return True
    return payload.get("version") != current_policy_version()
