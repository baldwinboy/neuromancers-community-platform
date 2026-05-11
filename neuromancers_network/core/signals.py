"""Signal handlers for guardian permission assignment."""

from djstripe.models.api import APIKey


def update_dj_stripe_keys(sender, instance, created, **kwargs):
    pk = instance.stripe_publishable_key
    sk = instance.stripe_secret_key

    # Delete any existing keys
    APIKey.objects.exclude(secret__in=[pk, sk]).delete()

    if pk:
        APIKey.objects.get_or_create_by_api_key(pk)
    if sk:
        APIKey.objects.get_or_create_by_api_key(sk)


def delete_dj_stripe_keys(sender, instance, **kwargs):
    """Delete dj-stripe keys when the ExternalAPISettings is deleted."""
    pk = instance.stripe_publishable_key
    sk = instance.stripe_secret_key

    APIKey.objects.filter(secret__in=[pk, sk]).delete()
