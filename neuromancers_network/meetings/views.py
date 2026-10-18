"""Small htmx fragments for meeting form pages."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView

from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.meetings.join import join_url_for
from neuromancers_network.meetings.join import resolve_join_target

DEFAULT_TIER_FIELD_NAME = "duration_tiers"


def join_meeting(request, kind, pk):
    """Redirect a participant to the provider's role-appropriate join link."""
    user = require_authenticated(request)
    if kind == "request":
        target = resolve_join_target(user, request_pk=pk)
    elif kind == "meeting":
        target = resolve_join_target(user, meeting_pk=pk)
    else:
        raise Http404
    if target is None:
        message = "You cannot join this session"
        raise PermissionDenied(message)
    return HttpResponseRedirect(join_url_for(user, target))


def tier_row(request):
    """Return one blank duration/price row for the tier repeater."""
    require_authenticated(request)
    name = request.GET.get("name") or DEFAULT_TIER_FIELD_NAME
    return render(request, "meetings/widgets/_tier_row.html", {"name": name})


class PaymentSuccessView(TemplateView):
    """Stripe Checkout return page shown after a successful payment."""

    template_name = "meetings/payment_success.html"


class PaymentCancelledView(TemplateView):
    """Stripe Checkout return page shown when payment is abandoned."""

    template_name = "meetings/payment_cancelled.html"
