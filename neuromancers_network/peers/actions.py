"""Action handlers for peer applications and Stripe Connect onboarding."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.dateparse import parse_datetime

from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.payments.services import ensure_payment_profile
from neuromancers_network.peers.models import PeerApplication
from neuromancers_network.peers.models import PeerAvailability
from neuromancers_network.peers.models.profile import PROVIDER_AGREEMENT_VERSION
from neuromancers_network.peers.services import is_eligible_peer


def _require_provider_agreement(user):
    profile = getattr(user, "peer_profile", None)
    if profile is None or not profile.has_accepted_provider_agreement:
        message = "Accept the care provider agreement first"
        raise PermissionDenied(message)
    return profile


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
    _require_provider_agreement(user)
    payment_profile = ensure_payment_profile(user)

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
    payment_profile = ensure_payment_profile(user)
    return HttpResponseRedirect(create_subscription_checkout(payment_profile, request))


def peer_open_stripe_dashboard(request, data):
    """Open the peer's Stripe Express dashboard, onboarding the account first."""
    from neuromancers_network.payments.services import (  # noqa: PLC0415
        ensure_stripe_account,
    )

    user = require_authenticated(request)
    _require_provider_agreement(user)
    if not is_eligible_peer(user):
        message = "Only eligible care providers can open the Stripe dashboard"
        raise PermissionDenied(message)

    ensure_stripe_account(user)
    payment_profile = getattr(user, "payment_profile", None)
    if payment_profile is None:
        message = "No payment profile for this user"
        raise PermissionDenied(message)
    return HttpResponseRedirect(payment_profile.create_express_dashboard_link())


def peer_accept_provider_agreement(request, data):
    user = require_authenticated(request)
    profile = getattr(user, "peer_profile", None)
    if profile is None:
        message = "Only care providers can accept the provider agreement"
        raise PermissionDenied(message)
    profile.provider_agreement_accepted_at = timezone.now()
    profile.provider_agreement_version = PROVIDER_AGREEMENT_VERSION
    profile.save(
        update_fields=[
            "provider_agreement_accepted_at",
            "provider_agreement_version",
            "updated_at",
        ],
    )
    return redirect_back(request)


def _parse_dt(value):
    """Parse an ISO datetime/date string into an aware datetime, or ``None``."""
    if value in (None, ""):
        return None
    parsed = parse_datetime(str(value))
    if parsed is None:
        as_date = parse_date(str(value))
        if as_date is None:
            return None
        parsed = timezone.datetime.combine(as_date, timezone.datetime.min.time())
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def availability_create(request, data):
    user = require_authenticated(request)
    window = PeerAvailability(
        peer=user,
        start=_parse_dt(data.get("start") or data.get("starts_at")),
        end=_parse_dt(data.get("end") or data.get("ends_at")),
        occurrence=(data.get("occurrence") or ""),
        occurrence_starts_at=_parse_dt(data.get("occurrence_starts_at")),
        occurrence_ends_at=_parse_dt(data.get("occurrence_ends_at")),
        reason=(data.get("reason") or ""),
    )
    window.full_clean()
    window.save()
    return redirect_back(request)


def availability_delete(request, data):
    user = require_authenticated(request)
    pk = (
        data.get("window")
        or data.get("availability")
        or data.get("pk")
        or data.get("target")
    )
    window = get_object_or_404(PeerAvailability, pk=pk)
    if window.peer_id != user.pk and not user.is_moderator:
        message = "You cannot manage this availability window"
        raise PermissionDenied(message)
    window.delete()
    return redirect_back(request)


HANDLERS = {
    "peers.apply": peers_apply,
    "peer.connect_stripe": peer_connect_stripe,
    "peer.subscribe": peer_subscribe,
    "peer.open_stripe_dashboard": peer_open_stripe_dashboard,
    "peer.accept_provider_agreement": peer_accept_provider_agreement,
    "availability.create": availability_create,
    "availability.delete": availability_delete,
}
