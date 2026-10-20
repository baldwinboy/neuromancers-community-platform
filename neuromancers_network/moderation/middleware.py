"""IP-ban enforcement middleware.

Enforcement is off by default (``BanSettings.ip_enforcement_enabled``) so the
app only records bans until trusted proxies (``RATELIMIT_TRUSTED_PROXIES``) are
configured — forwarded headers are otherwise spoofable.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied


class BanMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_block(request):
            message = "Access from this address is blocked"
            raise PermissionDenied(message)
        return self.get_response(request)

    @staticmethod
    def _should_block(request) -> bool:
        from neuromancers_network.core.audit import client_ip  # noqa: PLC0415
        from neuromancers_network.moderation.banning import ip_is_banned  # noqa: PLC0415
        from neuromancers_network.moderation.models import BanSettings  # noqa: PLC0415

        try:
            settings_obj = BanSettings.load()
        except Exception:  # noqa: BLE001 - table may not exist yet
            return False
        if not getattr(settings_obj, "ip_enforcement_enabled", False):
            return False
        return ip_is_banned(client_ip(request))
