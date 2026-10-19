"""Cookie-consent helpers (a single signed cookie)."""

from __future__ import annotations

from django.core import signing

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
