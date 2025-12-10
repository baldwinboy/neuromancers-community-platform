import stripe
from django.conf import settings
from django.http import HttpRequest
from wagtail.contrib.settings.registry import registry


def get_stripe_client(request: HttpRequest | None = None):
    # Use environment defaults
    if not request:
        return stripe.StripeClient(settings.STRIPE_API_SECRET_KEY)

    # Check if this has been overridden through the Wagtail Admin Settings
    stripe_settings = registry.get_by_natural_key("events", "StripeSettings").load(
        request_or_site=request
    )

    return stripe.StripeClient(
        stripe_settings.secret_key or settings.STRIPE_API_SECRET_KEY
    )


def get_stripe_secret_key(request: HttpRequest | None = None):
    # Use environment defaults
    if not request:
        return settings.STRIPE_API_SECRET_KEY

    # Check if this has been overridden through the Wagtail Admin Settings
    stripe_settings = registry.get_by_natural_key("events", "StripeSettings").load(
        request_or_site=request
    )

    return stripe_settings.secret_key or settings.STRIPE_API_SECRET_KEY


def get_stripe_client_id(request: HttpRequest | None = None):
    # Use environment defaults
    if not request:
        return settings.STRIPE_API_CLIENT_ID

    # Check if this has been overridden through the Wagtail Admin Settings
    stripe_settings = registry.get_by_natural_key("events", "StripeSettings").load(
        request_or_site=request
    )

    return stripe_settings.client_id or settings.STRIPE_API_CLIENT_ID


def get_stripe_redirect_url(request: HttpRequest | None = None):
    # Use environment defaults
    if not request:
        return settings.STRIPE_REDIRECT_URL

    # Check if this has been overridden through the Wagtail Admin Settings
    stripe_settings = registry.get_by_natural_key("events", "StripeSettings").load(
        request_or_site=request
    )

    return stripe_settings.redirect_url or settings.STRIPE_REDIRECT_URL


def get_stripe_oauth(code: str, request: HttpRequest | None = None):
    stripe.api_key = get_stripe_secret_key(request=request)
    return stripe.OAuth.token(grant_type="authorization_code", code=code)


def get_stripe_oauth_url(request: HttpRequest | None = None):
    stripe.client_id = get_stripe_client_id(request=request)
    redirect_uri = get_stripe_redirect_url(request=request)
    return stripe.OAuth.authorize_url(
        response_type="code", scope="read_write", redirect_uri=redirect_uri
    )


def is_stripe_account_ready(
    stripe_account_id: str, request: HttpRequest | None = None
) -> bool:
    stripe.api_key = get_stripe_secret_key(request=request)
    stripe.client_id = get_stripe_client_id(request=request)
    account = stripe.Account.retrieve(stripe_account_id)

    return (
        account.charges_enabled
        and account.payouts_enabled
        and account.details_submitted
    )
