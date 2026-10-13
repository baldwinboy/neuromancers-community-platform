"""Account audit trail helpers.

Sensitive account and moderation actions call :func:`record_audit` to append a
single immutable row to :class:`~neuromancers_network.core.models.AccountAuditLog`.
"""

from __future__ import annotations

__all__ = ["client_ip", "record_audit"]


def client_ip(request) -> str | None:
    """Return the best-effort client IP, proxy-trust aware when configured.

    Delegates to ``django_smart_ratelimit``'s extractor so the audit trail and
    the rate limiter agree on the client identity (honouring
    ``RATELIMIT_TRUSTED_PROXIES``). Falls back to ``REMOTE_ADDR``.
    """
    if request is None:
        return None
    meta = getattr(request, "META", {}) or {}
    try:
        from django_smart_ratelimit.policy import get_client_ip  # noqa: PLC0415

        ip = get_client_ip(request)
    except Exception:  # noqa: BLE001 - audit must never break the caller
        ip = None
    return ip or meta.get("REMOTE_ADDR") or None


def record_audit(  # noqa: PLR0913
    *,
    action: str,
    actor=None,
    user=None,
    request=None,
    event_type: str = "",
    changes: dict | None = None,
    reason: str = "",
):
    """Append one immutable audit row and return it.

    *actor* is the member performing the action; *user* is the subject. Both
    may be ``None`` (e.g. system or anonymous actions).
    """
    from neuromancers_network.core.models import AccountAuditLog  # noqa: PLC0415

    meta = (getattr(request, "META", None) or {}) if request is not None else {}
    return AccountAuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        user=user,
        action=action,
        event_type=event_type,
        ip_address=client_ip(request),
        user_agent=(meta.get("HTTP_USER_AGENT", "") or "")[:255],
        changes=changes or {},
        reason=reason or "",
    )
