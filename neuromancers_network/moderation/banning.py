"""Ban checks (email and IP).

Enforcement is a boolean check; the IP middleware stays in shadow mode until
``BanSettings.ip_enforcement_enabled`` is turned on.
"""

from __future__ import annotations

__all__ = ["email_is_banned", "ip_is_banned"]


def _normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def email_is_banned(email: str | None) -> bool:
    """Whether *email* matches an active exact address or whole-domain ban."""
    from django.db.models import Q  # noqa: PLC0415

    from .models import EmailBan  # noqa: PLC0415

    value = _normalize_email(email)
    if not value or "@" not in value:
        return False
    domain = value.rsplit("@", 1)[1]
    return (
        EmailBan.objects.filter(is_active=True)
        .filter(Q(value=value, is_domain=False) | Q(value=domain, is_domain=True))
        .exists()
    )


def ip_is_banned(ip: str | None) -> bool:
    """Whether *ip* has a non-expired ban."""
    if not ip:
        return False
    from .models import IPBan  # noqa: PLC0415

    ban = IPBan.objects.filter(ip_address=ip).first()
    return ban is not None and not ban.is_expired
