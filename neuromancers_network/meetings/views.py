"""Small htmx fragments for meeting form pages."""

from __future__ import annotations

from django.shortcuts import render
from django.views.generic import TemplateView

from neuromancers_network.core.actions import require_authenticated

DEFAULT_TIER_FIELD_NAME = "duration_tiers"


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
