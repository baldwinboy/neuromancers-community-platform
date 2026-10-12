"""Stripe Connect and webhook helpers for the platform."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import stripe
from djstripe.models import Account as StripeAccount
from djstripe.models import Customer as StripeCustomer
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


def ensure_payment_profile(user) -> PaymentProfile:
    """Return the user's payment profile, bootstrapping it lazily if missing.

    Creates the local ``PaymentProfile`` and its dj-stripe ``Customer`` on first
    use. Idempotent: an existing profile is returned untouched.
    """
    from neuromancers_network.payments.models import PaymentProfile  # noqa: PLC0415

    existing = getattr(user, "payment_profile", None)
    if existing is not None:
        return existing

    stripe_settings = StripeSettings.load()
    if not stripe_settings.secret_key:
        message = "Stripe secret key is not configured"
        raise ValueError(message)

    stripe.api_key = stripe_settings.secret_key
    customer = stripe.Customer.create(
        email=user.email,
        name=user.name or user.get_username(),
        metadata={"user_id": str(user.pk)},
    )
    stripe_customer = StripeCustomer.sync_from_stripe_data(
        customer,
        api_key=stripe_settings.secret_key,
    )
    profile, _created = PaymentProfile.objects.get_or_create(
        user=user,
        defaults={"stripe_customer_id": stripe_customer},
    )
    return profile


def ensure_stripe_account(user) -> StripeAccount:
    """Return the user's connected account, creating an express account if needed."""
    profile = ensure_payment_profile(user)
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


def receipt_url_for(payment_intent_id: str) -> str:
    """Return the Stripe hosted receipt URL for a synced payment intent, if any."""
    from djstripe.models import Charge as StripeCharge  # noqa: PLC0415

    if not payment_intent_id:
        return ""
    charge = StripeCharge.objects.filter(payment_intent_id=payment_intent_id).first()
    if charge is None:
        return ""
    return charge.receipt_url or ""


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
        customer=profile.stripe_customer_id_id,  # type: ignore[attr-defined]
        line_items=[{"price": price_id, "quantity": 1} for price_id in price_ids],
        success_url=request.build_absolute_uri("/pay/success/"),
        cancel_url=request.build_absolute_uri("/pay/cancelled/"),
        metadata={"payment_profile_id": str(profile.pk)},
    )
    url = session.url
    if url is None:
        message = "Stripe did not return a checkout URL"
        raise ValueError(message)
    return url


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
