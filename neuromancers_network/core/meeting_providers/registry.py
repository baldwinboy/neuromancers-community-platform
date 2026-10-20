"""Selects the active meeting provider from admin settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured

from neuromancers_network.core.meeting_providers.daily import DailyProvider
from neuromancers_network.core.meeting_providers.whereby import WherebyProvider

if TYPE_CHECKING:
    from neuromancers_network.core.meeting_providers.base import MeetingProvider

PROVIDERS: dict[str, type[MeetingProvider]] = {
    WherebyProvider.name: WherebyProvider,
    DailyProvider.name: DailyProvider,
}

DEFAULT_PROVIDER = WherebyProvider.name


def get_provider(name: str | None = None) -> MeetingProvider:
    """Return the requested provider, defaulting to the configured one.

    Parameters
    ----------
    name
        Explicit provider name. When omitted, the value of
        ``IntegrationSettings.meeting_provider`` is used, falling back to
        :data:`DEFAULT_PROVIDER`.
    """
    if name is None:
        from neuromancers_network.core.models import IntegrationSettings  # noqa: PLC0415

        name = IntegrationSettings.load().meeting_provider or DEFAULT_PROVIDER

    try:
        provider_class = PROVIDERS[name]
    except KeyError as exc:
        message = (
            f"Unknown meeting provider {name!r}. "
            f"Expected one of: {', '.join(sorted(PROVIDERS))}."
        )
        raise ImproperlyConfigured(message) from exc

    return provider_class()
