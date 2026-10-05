"""Internal event bus.

``emit`` is the single entry point that domain code (or signal receivers) calls
when a business event happens. It appends a row to ``NotificationEventLog``
(the durable store / "webhook source") and then notifies every registered,
active ``EventSubscriber`` whose ``event_type`` matches.

The bus is deliberately failure-isolated: subscriber errors are logged, never
raised, so recording an event can never break the caller's transaction.
"""

from __future__ import annotations

import logging

from .models.event_type import NotificationEventType
from .registry import get_subscriber_models

logger = logging.getLogger(__name__)


class UnknownEventTypeError(ValueError):
    """Raised when ``emit`` is called with an unrecognized event type."""

    def __init__(self, event_type):
        super().__init__(f"Unknown event type: {event_type!r}")


def emit(event_type, *, payload=None, event_ref=""):
    """Record *event_type* and dispatch it to active subscribers.

    Parameters
    ----------
    event_type : str | NotificationEventType
        One of :class:`NotificationEventType`.
    payload : dict | None
        Normalized context snapshot; see ``NotificationEventLog.payload``.
    event_ref : str
        Optional stable reference for dedupe/idempotency, e.g.
        ``"meetingrequest.42.cancelled"``.

    Returns
    -------
    NotificationEventLog
        The stored event row (also handed to subscribers).

    Raises
    ------
    UnknownEventTypeError
        If *event_type* is not a known :class:`NotificationEventType`.
    """
    if event_type not in NotificationEventType.values:
        raise UnknownEventTypeError(event_type)

    from .models.event_log import NotificationEventLog  # noqa: PLC0415

    log_entry = NotificationEventLog.objects.create(
        event_type=event_type,
        payload=payload or {},
        event_ref=event_ref or "",
    )
    _dispatch(log_entry)
    return log_entry


def _dispatch(log_entry) -> None:
    """Call ``handle_event`` on matching active subscribers."""
    for subscriber in collect_active_subscribers(log_entry.event_type):
        try:
            subscriber.handle_event(log_entry)
        except Exception:
            # Subscriber failures must never break the caller's transaction.
            logger.exception(
                "Subscriber %r failed handling event %s",
                subscriber,
                log_entry.event_type,
            )


def collect_active_subscribers(event_type):
    """Yield active subscriber instances registered for *event_type*."""
    for model in get_subscriber_models():
        manager = getattr(model, "_default_manager", None)
        if manager is None:
            manager = getattr(model, "objects", None)
        if manager is None:
            continue
        yield from manager.filter(is_active=True, event_type=event_type)
