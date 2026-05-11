from django.urls import path

from neuromancers_network.events.views.stripe import StripeAccountStatusView
from neuromancers_network.events.views.stripe import StripeCheckoutView
from neuromancers_network.events.views.stripe import StripeOnboardingCallbackView
from neuromancers_network.events.views.stripe import StripeOnboardingView
from neuromancers_network.events.views.stripe import StripeSubscriptionCheckoutView

app_name = "events"

urlpatterns = [
    # Stripe Connect onboarding
    path("onboarding/", StripeOnboardingView.as_view(), name="stripe-onboarding"),
    path("onboarding/callback/", StripeOnboardingCallbackView.as_view(), name="stripe-onboarding-callback"),
    # Account status
    path("account/status/", StripeAccountStatusView.as_view(), name="stripe-account-status"),
    # Checkout sessions
    path("checkout/", StripeCheckoutView.as_view(), name="stripe-checkout"),
    # Subscriptions
    path("subscribe/", StripeSubscriptionCheckoutView.as_view(), name="stripe-subscribe"),
]
