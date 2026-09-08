"""Registry of concrete event subscriber models.

Concrete subclasses of ``EventSubscriber`` register themselves here at import
time (via ``__init_subclass__``). Because Django models are imported when their
apps load, this registry is fully populated before any request or worker
handles an event, so ``events.emit`` can always discover active subscribers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import Model

subscriber_model_registry: dict[str, type[Model]] = {}


def register_subscriber_model(model: type[Model]) -> None:
    """Add *model* to the subscriber registry keyed by its app label."""
    subscriber_model_registry[model._meta.label_lower] = model  # noqa: SLF001


def get_subscriber_models() -> list[type[Model]]:
    """Return all registered concrete subscriber model classes."""
    return list(subscriber_model_registry.values())
