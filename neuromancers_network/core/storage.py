"""Deconstructible storage callables for ``STORAGES`` aliases.

``FileField`` accepts a ``Storage`` instance or a callable, but not an alias
string. A deconstructible callable keeps migrations referencing a stable path
while still resolving the configured alias (local filesystem in development,
the private bucket in production).
"""

from __future__ import annotations

from django.core.files.storage import storages
from django.utils.deconstruct import deconstructible


@deconstructible(path="neuromancers_network.core.storage.ExportsStorage")
class ExportsStorage:
    """Return the private ``exports`` storage alias."""

    def __call__(self):
        return storages["exports"]
