"""Signal handlers keeping dj-stripe API keys in sync with the Wagtail settings."""

import logging

from djstripe.exceptions import InvalidStripeAPIKey
from djstripe.models.api import APIKey

from neuromancers_network.core.i18n import bust_localization_cache as bust

logger = logging.getLogger(__name__)


def _get_or_create_api_key(key: str) -> None:
    """Register *key* with dj-stripe, ignoring malformed placeholder values."""
    try:
        APIKey.objects.get_or_create_by_api_key(key)
    except InvalidStripeAPIKey:
        logger.warning("Ignoring invalid Stripe API key configured in settings")


def update_dj_stripe_keys(sender, instance, **kwargs):
    """Sync dj-stripe API keys whenever the Stripe settings are saved."""
    publishable_key = instance.publishable_key
    secret_key = instance.secret_key

    if publishable_key:
        _get_or_create_api_key(publishable_key)
    if secret_key:
        _get_or_create_api_key(secret_key)

    APIKey.objects.exclude(secret__in=[publishable_key, secret_key]).delete()


def delete_dj_stripe_keys(sender, instance, **kwargs):
    """Delete the dj-stripe keys belonging to deleted Stripe settings."""
    publishable_key = instance.publishable_key
    secret_key = instance.secret_key

    APIKey.objects.filter(secret__in=[publishable_key, secret_key]).delete()


def bust_localization_cache(sender, instance, **kwargs):
    """Drop the cached localization configuration when settings change."""
    bust()
