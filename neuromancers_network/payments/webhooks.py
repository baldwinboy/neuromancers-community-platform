"""Helpers for syncing dj-stripe objects from account-scoped webhook events."""

from __future__ import annotations


def event_account_id(event) -> str | None:
    """Return the connected account id carried by *event*, if any."""
    account = getattr(event, "djstripe_owner_account", None)
    return getattr(account, "id", None)


def sync_from_event(model_cls, data, event):
    """Sync *data* into *model_cls*, associating it with the event's account.

    ``sync_from_stripe_data`` derives the owner from the Stripe object; webhook
    payloads are plain dicts, so account-scoped events need the owner set
    explicitly from ``event.djstripe_owner_account``.
    """
    instance = model_cls.sync_from_stripe_data(data, api_key=event.default_api_key)
    account_id = event_account_id(event)
    if (
        account_id
        and getattr(instance, "djstripe_owner_account_id", None) != account_id
    ):
        instance.djstripe_owner_account_id = account_id
        instance.save(update_fields=["djstripe_owner_account"])
    return instance
