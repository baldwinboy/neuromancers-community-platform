"""Action handlers for peer applications and Stripe Connect onboarding."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect

from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.peers.models import PeerApplication
from neuromancers_network.peers.services import is_eligible_peer


def peers_apply(request, data):
    user = require_authenticated(request)
    if is_eligible_peer(user):
        message = "Already an eligible peer"
        raise PermissionDenied(message)
    if PeerApplication.objects.filter(user=user).exists():
        message = "Peer application already submitted"
        raise PermissionDenied(message)

    reason = data.get("reason", "") if hasattr(data, "get") else ""
    PeerApplication.objects.create(user=user, reason=reason)
    return redirect_back(request)


def peer_connect_stripe(request, data):
    user = require_authenticated(request)
    payment_profile = getattr(user, "payment_profile", None)
    if payment_profile is None:
        message = "No payment profile for this user"
        raise PermissionDenied(message)

    fallback = request.build_absolute_uri(user.get_absolute_url())
    refresh_url = data.get("refresh_url") or fallback
    return_url = data.get("return_url") or fallback
    link = payment_profile.create_stripe_onboarding_link(
        refresh_url=refresh_url,
        return_url=return_url,
    )
    return HttpResponseRedirect(link.url)


def peer_subscribe(request, data):
    """Start the peer subscription checkout (Stripe test mode)."""
    from neuromancers_network.payments.services import (  # noqa: PLC0415
        create_subscription_checkout,
    )

    user = require_authenticated(request)
    payment_profile = getattr(user, "payment_profile", None)
    if payment_profile is None:
        message = "No payment profile for this user"
        raise PermissionDenied(message)
    return HttpResponseRedirect(create_subscription_checkout(payment_profile, request))


def peer_open_stripe_dashboard(request, data):
    """Open the peer's Stripe Express dashboard, onboarding the account first."""
    from neuromancers_network.payments.services import (  # noqa: PLC0415
        ensure_stripe_account,
    )

    user = require_authenticated(request)
    if not is_eligible_peer(user):
        message = "Only eligible care providers can open the Stripe dashboard"
        raise PermissionDenied(message)

    ensure_stripe_account(user)
    payment_profile = getattr(user, "payment_profile", None)
    if payment_profile is None:
        message = "No payment profile for this user"
        raise PermissionDenied(message)
    return HttpResponseRedirect(payment_profile.create_express_dashboard_link())


HANDLERS = {
    "peers.apply": peers_apply,
    "peer.connect_stripe": peer_connect_stripe,
    "peer.subscribe": peer_subscribe,
    "peer.open_stripe_dashboard": peer_open_stripe_dashboard,
}
