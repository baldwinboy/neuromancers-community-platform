"""Stripe Connect and webhook helpers for the platform."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import stripe
from djstripe.models import Account as StripeAccount
from djstripe.models import WebhookEndpoint as StripeWebhookEndpoint

from neuromancers_network.core.models import StripeSettings

if TYPE_CHECKING:
    from neuromancers_network.payments.models import PaymentProfile

logger = logging.getLogger(__name__)

DEFAULT_WEBHOOK_EVENTS = [
    "account.updated",
    "checkout.session.completed",
    "charge.refunded",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
]


def _individual_payload(user) -> dict:
    parts = (user.name or "").split(" ", 1)
    individual = {
        "first_name": parts[0] if parts else "",
        "last_name": parts[1] if len(parts) > 1 else "",
    }
    date_of_birth = getattr(user, "date_of_birth", None)
    if date_of_birth is not None:
        individual["dob"] = {
            "day": date_of_birth.day,
            "month": date_of_birth.month,
            "year": date_of_birth.year,
        }
    return individual


def ensure_stripe_account(user) -> StripeAccount:
    """Return the user's connected account, creating an express account if needed."""
    profile = getattr(user, "payment_profile", None)
    if profile is None:
        message = "No payment profile for this user"
        raise ValueError(message)
    if profile.stripe_connect_account_id_id:
        existing = profile.stripe_connect_account_id
        if existing is not None:
            return existing

    stripe_settings = StripeSettings.load()
    if not stripe_settings.secret_key:
        message = "Stripe secret key is not configured"
        raise ValueError(message)

    country = getattr(getattr(user, "user_profile", None), "country", "") or "GB"

    stripe.api_key = stripe_settings.secret_key
    account = stripe.Account.create(
        type="express",
        country=country,
        email=user.email,
        business_type="individual",
        individual=_individual_payload(user),  # type: ignore[arg-type]
        capabilities={
            "transfers": {"requested": True},
            "card_payments": {"requested": True},
        },
    )
    stripe_account = StripeAccount.sync_from_stripe_data(
        account,
        api_key=stripe_settings.secret_key,
    )
    profile.stripe_connect_account_id = stripe_account
    profile.save(update_fields=["stripe_connect_account_id", "updated_at"])
    return stripe_account


def create_subscription_checkout(profile: PaymentProfile, request) -> str:
    """Create a Stripe Checkout session for the peer subscription plan.

    Uses the price IDs configured on ``PeerRequirementsSettings``. Intended for
    Stripe test mode during development.
    """
    from neuromancers_network.peers.models import (  # noqa: PLC0415
        PeerRequirementsSettings,
    )

    stripe_settings = StripeSettings.load(request)
    if not stripe_settings.is_ready:
        message = "Stripe is not configured"
        raise ValueError(message)

    price_ids = PeerRequirementsSettings.load().peer_plan_price_ids or []
    if not price_ids:
        message = "No peer plan prices are configured"
        raise ValueError(message)

    stripe.api_key = stripe_settings.secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=profile.stripe_customer_id_id,
        line_items=[{"price": price_id, "quantity": 1} for price_id in price_ids],
        success_url=request.build_absolute_uri("/pay/success/"),
        cancel_url=request.build_absolute_uri("/pay/cancelled/"),
        metadata={"payment_profile_id": str(profile.pk)},
    )
    return session.url


def create_express_dashboard_link(profile: PaymentProfile) -> str:
    """Create a Stripe Express dashboard login link for *profile*."""
    stripe_settings = StripeSettings.load()
    if not stripe_settings.secret_key:
        message = "Stripe secret key is not configured"
        raise ValueError(message)

    account_id = profile.stripe_connect_account_id_id  # type: ignore[attr-defined]
    if not account_id:
        message = "Payment profile has no connected Stripe account"
        raise ValueError(message)

    stripe.api_key = stripe_settings.secret_key
    link = stripe.Account.create_login_link(account_id)
    return link.url


def create_webhook_endpoint(
    *,
    url: str,
    enabled_events=None,
    djstripe_uuid=None,
) -> str:
    """Create the platform webhook endpoint, sync it and store its secret."""
    stripe_settings = StripeSettings.load()
    if not stripe_settings.secret_key:
        message = "Stripe secret key is not configured"
        raise ValueError(message)

    stripe.api_key = stripe_settings.secret_key
    endpoint = stripe.WebhookEndpoint.create(
        url=url,
        enabled_events=enabled_events or DEFAULT_WEBHOOK_EVENTS,  # type: ignore[arg-type]
    )
    secret = endpoint.secret
    if secret is None:
        message = "Stripe did not return a webhook secret"
        raise ValueError(message)

    local_endpoint = StripeWebhookEndpoint.sync_from_stripe_data(
        endpoint,
        api_key=stripe_settings.secret_key,
    )
    if djstripe_uuid is not None:
        local_endpoint.djstripe_uuid = djstripe_uuid
        local_endpoint.save(update_fields=["djstripe_uuid"])

    StripeSettings.objects.filter(pk=stripe_settings.pk).update(
        webhook_secret=secret,
    )
    return secret
