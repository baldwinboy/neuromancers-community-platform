from __future__ import annotations

import logging

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from djstripe.models import Account as StripeAccount
from djstripe.models import Session as StripeSession

from neuromancers_network.common.stripe import Stripe
from neuromancers_network.events.checkout import CheckoutStrategy
from neuromancers_network.events.checkout import build_destination_checkout_params
from neuromancers_network.events.checkout import build_separate_charges_checkout_params
from neuromancers_network.events.checkout import determine_strategy
from neuromancers_network.events.models import PaymentStatus
from neuromancers_network.events.models import SessionBooking

logger = logging.getLogger(__name__)
User = get_user_model()


class StripeOnboardingView(View):
    """Redirect the host to Stripe's OAuth authorization page."""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)

        stripe_helper = Stripe()
        url = stripe_helper.get_oauth_url()
        return redirect(url)


class StripeOnboardingCallbackView(View):
    """Handle the OAuth redirect from Stripe after Connect onboarding."""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)

        code = request.GET.get("code")
        error = request.GET.get("error")

        if error or not code:
            logger.warning("Stripe OAuth error: %s", error)
            return redirect("users:detail", username=request.user.username)

        stripe_helper = Stripe()
        try:
            response = stripe_helper.get_oauth_token(code)
            stripe_account_id = response["stripe_user_id"]

            account_data = stripe.Account.retrieve(
                stripe_account_id,
                api_key=stripe_helper.secret_key,
            )
            account, _ = StripeAccount._get_or_create_from_stripe_object(
                account_data,
                api_key=stripe_helper.secret_key,
            )
            request.user.stripe_account = account
            request.user.save(update_fields=["stripe_account"])
            logger.info(
                "Connected Stripe account %s for user %s",
                stripe_account_id,
                request.user,
            )
        except Exception as e:
            logger.exception("Failed to complete Stripe OAuth: %s", e)

        return redirect("users:detail", username=request.user.username)


class StripeAccountStatusView(View):
    """Return the readiness status of a user's connected Stripe account."""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=403)

        account = request.user.stripe_account
        if not account:
            return JsonResponse(
                {
                    "connected": False,
                    "ready": False,
                    "onboarding_url": Stripe().get_oauth_url(),
                }
            )

        try:
            stripe_helper = Stripe()
            ready = stripe_helper.is_account_ready(account.id)
            return JsonResponse(
                {
                    "connected": True,
                    "ready": ready,
                }
            )
        except Exception as e:
            logger.exception("Failed to check account status: %s", e)
            return JsonResponse(
                {
                    "connected": True,
                    "ready": False,
                    "error": str(e),
                },
                status=500,
            )


class StripeCheckoutView(View):
    """Create a Stripe Checkout Session for one or more unpaid bookings.

    Uses dj-stripe's ``Session._api_create()`` to create the session via the
    Stripe API, then syncs the result locally via ``Session.sync_from_stripe_data()``.
    """

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=403)

        booking_ids = request.POST.getlist("booking_ids")
        if not booking_ids:
            return JsonResponse({"error": "No bookings specified"}, status=400)

        bookings = SessionBooking.objects.filter(
            id__in=booking_ids,
            attendee=request.user,
            payment_status=PaymentStatus.REQUIRED,
        )

        if not bookings:
            return JsonResponse({"error": "No unpaid bookings found"}, status=404)

        strategy = determine_strategy(list(bookings))
        if strategy is None:
            return JsonResponse({"error": "All bookings are free"}, status=400)

        success_url = request.build_absolute_uri("/pay/success/")
        cancel_url = request.build_absolute_uri("/pay/cancelled/")

        stripe_helper = Stripe()

        try:
            if strategy == CheckoutStrategy.DESTINATION:
                params = build_destination_checkout_params(
                    bookings[0],
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
            else:
                params = build_separate_charges_checkout_params(
                    list(bookings),
                    success_url=success_url,
                    cancel_url=cancel_url,
                )

            # Use dj-stripe's Session._api_create to create the Checkout Session
            # via the Stripe API, then sync the result locally.
            stripe.api_key = stripe_helper.secret_key
            stripe_data = StripeSession._api_create(**params)
            StripeSession.sync_from_stripe_data(stripe_data)

            checkout_id = stripe_data["id"]

            for booking in bookings:
                booking.payment_status = PaymentStatus.CHECKOUT_CREATED
                booking.checkout_reference = checkout_id
                booking.save(update_fields=["payment_status", "checkout_reference"])

            logger.info(
                "Created Checkout Session %s for user %s (%d bookings)",
                checkout_id,
                request.user,
                len(bookings),
            )

            return JsonResponse({"checkout_url": stripe_data["url"]})

        except Exception as e:
            logger.exception("Failed to create Checkout Session: %s", e)
            return JsonResponse({"error": str(e)}, status=500)


class StripeSubscriptionCheckoutView(View):
    """Create a Stripe Checkout Session for a verified peer subscription.

    Uses dj-stripe's ``Session._api_create()`` to create the subscription
    checkout via the Stripe API.
    """

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=403)

        price_id = request.POST.get("price_id", "")
        if not price_id:
            return JsonResponse({"error": "No price_id specified"}, status=400)

        stripe_helper = Stripe()
        success_url = request.build_absolute_uri("/settings/")
        cancel_url = request.build_absolute_uri("/sessions/")

        try:
            params = {
                "mode": "subscription",
                "line_items": [
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": {
                    "user_id": str(request.user.id),
                },
            }

            stripe.api_key = stripe_helper.secret_key
            stripe_data = StripeSession._api_create(**params)
            StripeSession.sync_from_stripe_data(stripe_data)

            logger.info(
                "Created subscription checkout %s for user %s",
                stripe_data["id"],
                request.user,
            )
            return JsonResponse({"checkout_url": stripe_data["url"]})
        except Exception as e:
            logger.exception("Failed to create subscription checkout: %s", e)
            return JsonResponse({"error": str(e)}, status=500)
