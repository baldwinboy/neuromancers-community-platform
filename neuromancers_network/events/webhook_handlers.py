import logging

import stripe
from django.contrib.auth import get_user_model
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Customer as StripeCustomer
from djstripe.models import Subscription as StripeSubscription

logger = logging.getLogger(__name__)


@djstripe_receiver("checkout.session.completed")
def handle_checkout_completed(sender, event, **kwargs):
    """Process checkout.session.completed — update booking payment status and handle transfers."""
    from neuromancers_network.events.models import SessionBooking  # noqa: PLC0415

    session_data = event.data["object"]
    checkout_id = session_data["id"]
    mode = session_data.get("mode", "payment")

    if mode == "subscription":
        _handle_subscription_checkout(session_data)
        return

    payment_status = session_data.get("payment_status", "unpaid")

    bookings = SessionBooking.objects.filter(checkout_reference=checkout_id)

    if payment_status == "paid":
        for booking in bookings:
            try:
                booking.mark_processing()
                booking.mark_paid()
                booking.save()
            except Exception:
                logger.exception("Payment transition failed for booking %s", booking.id)

        if len(bookings) > 1:
            _execute_transfers(list(bookings))

        logger.info(
            "Processed paid checkout %s for %d bookings",
            checkout_id,
            len(bookings),
        )
    elif payment_status == "unpaid":
        for booking in bookings:
            try:
                booking.mark_processing()
                booking.save()
            except Exception:
                logger.exception(
                    "Processing transition failed for booking %s",
                    booking.id,
                )
        logger.info(
            "Processing async checkout %s for %d bookings",
            checkout_id,
            len(bookings),
        )


@djstripe_receiver("checkout.session.expired")
def handle_checkout_expired(sender, event, **kwargs):
    """Process checkout.session.expired — expire payment on related bookings."""
    from neuromancers_network.events.models import SessionBooking  # noqa: PLC0415

    session_data = event.data["object"]
    checkout_id = session_data["id"]

    bookings = SessionBooking.objects.filter(checkout_reference=checkout_id)
    for booking in bookings:
        booking.expire_payment()
        booking.save()

    logger.info("Expired checkout %s for %d bookings", checkout_id, len(bookings))


@djstripe_receiver("customer.subscription.updated")
def handle_subscription_updated(sender, event, **kwargs):
    """Sync subscription status and promote/demote user tier."""

    stripe_sub_data = event.data["object"]
    subscription_id = stripe_sub_data["id"]

    try:
        sub, _ = StripeSubscription._get_or_create_from_stripe_object(stripe_sub_data)
    except Exception:
        logger.exception("Failed to sync subscription %s", subscription_id)
        return

    customer = sub.customer
    user = customer.subscriber if customer else None
    if not user:
        logger.warning("No subscriber for subscription %s", subscription_id)
        return

    if sub.status == "active":
        try:
            user.profile.promote_to_verified_peer()
            user.profile.save()
            logger.info("Promoted user %s to verified_peer", user.id)
        except Exception:
            logger.exception("Failed to promote user %s to verified_peer", user.id)
    elif sub.status in ("canceled", "unpaid", "incomplete_expired"):
        try:
            if user.profile.tier_state == "verified_peer":
                user.profile.demote_to_seeker()
                user.profile.save()
                logger.info("Demoted user %s from verified_peer", user.id)
        except Exception:
            logger.exception("Failed to demote user %s", user.id)


@djstripe_receiver("customer.subscription.deleted")
def handle_subscription_deleted(sender, event, **kwargs):
    """Handle subscription cancellation — delegate to the updated handler."""
    handle_subscription_updated(sender, event, **kwargs)


def _handle_subscription_checkout(session_data):
    """Sync subscription and customer records from a subscription-mode checkout."""

    User = get_user_model()
    user_id = session_data.get("metadata", {}).get("user_id")
    subscription_id = session_data.get("subscription")
    customer_id = session_data.get("customer")

    if not user_id or not subscription_id:
        logger.warning(
            "Missing user_id or subscription in checkout %s",
            session_data["id"],
        )
        return

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.exception("User %s not found for subscription checkout", user_id)
        return

    try:
        stripe_sub_data = stripe.Subscription.retrieve(subscription_id)
        StripeSubscription._get_or_create_from_stripe_object(stripe_sub_data)
        stripe_customer_data = stripe.Customer.retrieve(customer_id)
        cust, _ = StripeCustomer._get_or_create_from_stripe_object(stripe_customer_data)
        if cust.subscriber != user:
            cust.subscriber = user
            cust.save()
    except Exception:
        logger.exception(
            "Failed to sync subscription/customer for checkout %s",
            session_data["id"],
        )


def _execute_transfers(bookings):
    """Create Stripe Transfers for multi-session checkout."""
    charge_id = None
    for booking in bookings:
        if booking.checkout_reference:
            try:
                checkout = stripe.Checkout.Session.retrieve(booking.checkout_reference)
                charge_id = checkout.get("payment_intent")
                break
            except Exception:
                continue

    if not charge_id or len(bookings) <= 1:
        return

    try:
        from neuromancers_network.events.checkout import plan_transfers

        _, transfers = plan_transfers(charge_id, list(bookings))
        for transfer in transfers:
            stripe.Transfer.create(
                amount=transfer.amount_subunit,
                currency=transfer.currency,
                destination=transfer.destination_account,
                transfer_group=charge_id,
            )
        logger.info("Created %d transfers for charge %s", len(transfers), charge_id)
    except Exception:
        logger.exception("Transfer creation failed for charge %s", charge_id)
