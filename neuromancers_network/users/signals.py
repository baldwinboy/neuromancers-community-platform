"""Emit account lifecycle events onto the inbox event bus."""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.db.models.signals import pre_delete
from django_fsm.signals import post_transition

from neuromancers_network.inbox.events import emit
from neuromancers_network.inbox.payloads import account_lifecycle_payload

logger = logging.getLogger(__name__)


def _emit_account_event(
    event_type: str,
    user,
    *,
    event_ref: str,
    skip_in_app: bool = False,
) -> None:
    try:
        payload = account_lifecycle_payload(user, actor=user, recipients=[user])
        payload["skip_in_app"] = skip_in_app
        emit(event_type, payload=payload, event_ref=event_ref)
    except Exception:
        logger.exception("Failed to emit %s for user %s", event_type, user.pk)


def emit_account_created(sender, instance, created, **kwargs):
    if created:
        _emit_account_event(
            "account_created",
            instance,
            event_ref=f"user.{instance.pk}.created",
        )


def emit_account_deleted(sender, instance, **kwargs):
    # ``pre_delete`` fires while the row still exists, so the email bridge can
    # resolve the departing member. In-app delivery is pointless (the recipient
    # is being removed), so skip it and deliver by email only.
    _emit_account_event(
        "account_deleted",
        instance,
        event_ref=f"user.{instance.pk}.deleted",
        skip_in_app=True,
    )


def emit_account_degraded(sender, instance, name, **kwargs):
    if name != "suspend_staff":
        return
    _emit_account_event(
        "account_degraded",
        instance,
        event_ref=f"user.{instance.pk}.degraded",
    )


def connect_signals():
    from neuromancers_network.users.models import User  # noqa: PLC0415

    post_save.connect(
        emit_account_created,
        sender=User,
        dispatch_uid="users.signals.account_created",
    )
    pre_delete.connect(
        emit_account_deleted,
        sender=User,
        dispatch_uid="users.signals.account_deleted",
    )
    post_transition.connect(
        emit_account_degraded,
        sender=User,
        dispatch_uid="users.signals.account_degraded",
    )
