"""Stripe Connect and webhook helpers for the platform."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import stripe
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from djstripe.enums import SubscriptionStatus
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
    "payment_intent.succeeded",
    "charge.refunded",
    "charge.dispute.created",
    "charge.dispute.closed",
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
        idempotency_key=f"customer:{user.pk}",
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
        try:
            existing = profile.stripe_connect_account_id
        except ObjectDoesNotExist:
            existing = None
        if existing is not None:
            return existing

    stripe_settings = StripeSettings.load()
    if not stripe_settings.secret_key:
        message = "Stripe secret key is not configured"
        raise ValueError(message)

    country = (
        getattr(getattr(user, "user_profile", None), "country", "")
        or stripe_settings.connect_country
        or "GB"
    )

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
        idempotency_key=f"connect-account:{user.pk}",
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


class StripeBalanceError(ValueError):
    """A connected account still holds funds and cannot be deleted."""


def _balance_minor_units(balance) -> int:
    total = 0
    for bucket in ("available", "pending"):
        for entry in getattr(balance, bucket, None) or []:
            total += int(entry.get("amount", 0))
    return total


def _cancel_active_subscription(profile: PaymentProfile) -> None:
    peer_subscription = getattr(profile, "peer_subscription", None)
    if peer_subscription is None:
        return
    subscription_id = peer_subscription.subscription_id
    if not subscription_id:
        return
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
    except stripe.StripeError as exc:
        logger.exception(
            "Failed to read the Stripe subscription for profile %s",
            profile.pk,
        )
        message = "Could not read the Stripe subscription"
        raise ValueError(message) from exc
    if subscription.status in {
        SubscriptionStatus.canceled,
        SubscriptionStatus.incomplete_expired,
    }:
        return
    try:
        cancel_subscription(profile, at_period_end=False)
    except stripe.StripeError as exc:
        logger.exception(
            "Failed to cancel the Stripe subscription for profile %s",
            profile.pk,
        )
        message = "Could not cancel the Stripe subscription"
        raise ValueError(message) from exc


def disconnect_stripe_account(profile: PaymentProfile) -> None:
    """Cancel billing, then delete the peer's Stripe account and unlink it."""
    account_id = profile.stripe_connect_account_id_id
    if not account_id:
        return

    stripe_settings = StripeSettings.load()
    if not stripe_settings.secret_key:
        message = "Stripe secret key is not configured"
        raise ValueError(message)

    stripe.api_key = stripe_settings.secret_key
    try:
        balance = stripe.Balance.retrieve(stripe_account=account_id)
    except stripe.StripeError as exc:
        logger.exception("Failed to read Stripe balance for account %s", account_id)
        message = "Could not verify the Stripe account balance"
        raise ValueError(message) from exc

    if _balance_minor_units(balance) > 0:
        message = "The Stripe account still holds funds; withdraw them first"
        raise StripeBalanceError(message)

    _cancel_active_subscription(profile)

    try:
        stripe.Account.delete(account_id)
    except stripe.InvalidRequestError as exc:
        if getattr(exc, "code", None) != "resource_missing":
            logger.exception("Failed to delete Stripe account %s", account_id)
            message = "Could not delete the connected Stripe account"
            raise ValueError(message) from exc
    except stripe.StripeError as exc:
        logger.exception("Failed to delete Stripe account %s", account_id)
        message = "Could not delete the connected Stripe account"
        raise ValueError(message) from exc

    profile.stripe_connect_account_id = None
    profile.kyc_completed = False
    profile.save(
        update_fields=[
            "stripe_connect_account_id",
            "kyc_completed",
            "updated_at",
        ],
    )


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


def _peer_subscription_id(profile: PaymentProfile) -> str:
    peer_subscription = getattr(profile, "peer_subscription", None)
    subscription_id = (
        peer_subscription.subscription_id if peer_subscription is not None else ""
    )
    if not subscription_id:
        message = "Payment profile has no peer subscription"
        raise ValueError(message)
    return subscription_id


def _set_paused(profile: PaymentProfile, *, paused: bool) -> None:
    peer_subscription = getattr(profile, "peer_subscription", None)
    if peer_subscription is None:
        return
    if paused and peer_subscription.paused_at is None:
        peer_subscription.paused_at = timezone.now()
        peer_subscription.save(update_fields=["paused_at", "updated_at"])
    elif not paused and peer_subscription.paused_at is not None:
        peer_subscription.paused_at = None
        peer_subscription.save(update_fields=["paused_at", "updated_at"])


def pause_subscription(profile: PaymentProfile) -> None:
    """Pause collection on the peer's subscription.

    The Stripe status is left unchanged (as Stripe documents), so eligibility is
    tracked by the local ``PeerSubscription.paused_at`` flag.
    """
    stripe_settings = StripeSettings.load()
    if not stripe_settings.secret_key:
        message = "Stripe secret key is not configured"
        raise ValueError(message)

    stripe.api_key = stripe_settings.secret_key
    stripe.Subscription.modify(
        _peer_subscription_id(profile),
        pause_collection={"behavior": "void"},
    )
    _set_paused(profile, paused=True)


def resume_subscription(profile: PaymentProfile) -> None:
    """Resume a paused subscription, resetting the billing cycle anchor."""
    stripe_settings = StripeSettings.load()
    if not stripe_settings.secret_key:
        message = "Stripe secret key is not configured"
        raise ValueError(message)

    stripe.api_key = stripe_settings.secret_key
    stripe.Subscription.resume(
        _peer_subscription_id(profile),
        billing_cycle_anchor="now",
        proration_behavior="create_prorations",
    )
    _set_paused(profile, paused=False)


def cancel_subscription(profile: PaymentProfile, *, at_period_end: bool) -> None:
    """Cancel the peer's subscription immediately or at the period end."""
    stripe_settings = StripeSettings.load()
    if not stripe_settings.secret_key:
        message = "Stripe secret key is not configured"
        raise ValueError(message)

    subscription_id = _peer_subscription_id(profile)
    stripe.api_key = stripe_settings.secret_key
    if at_period_end:
        stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
    else:
        stripe.Subscription.cancel(subscription_id)


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
    stripe_settings.refresh_from_db(fields=["webhook_secret"])
    return secret
