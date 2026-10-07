"""Shared helpers for developer-defined actions.

Action handlers have the signature ``handler(request, data) -> HttpResponse |
None`` where ``data`` is the submitted POST data, matching the daisIE action
runner. These helpers keep the per-app handlers small.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme


def require_authenticated(request):
    """Return ``request.user`` or raise ``PermissionDenied``."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        message = "Authentication required"
        raise PermissionDenied(message)
    return user


def as_bool(value) -> bool:
    """Coerce common truthy strings from form/action data to ``bool``."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def as_list(data, key: str) -> list:
    """Return a list for *key* from a QueryDict-like mapping."""
    getlist = getattr(data, "getlist", None)
    if getlist is not None:
        return list(getlist(key))
    value = data.get(key) if hasattr(data, "get") else None
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def redirect_back(request) -> HttpResponseRedirect:
    target = request.headers.get("referer") or "/"
    if not url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        target = "/"
    return HttpResponseRedirect(target)
