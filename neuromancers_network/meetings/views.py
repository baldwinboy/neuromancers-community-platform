"""Small htmx fragments for meeting form pages."""

from __future__ import annotations

from django.shortcuts import render

from neuromancers_network.core.actions import require_authenticated

DEFAULT_TIER_FIELD_NAME = "duration_tiers"


def tier_row(request):
    """Return one blank duration/price row for the tier repeater."""
    require_authenticated(request)
    name = request.GET.get("name") or DEFAULT_TIER_FIELD_NAME
    return render(request, "meetings/widgets/_tier_row.html", {"name": name})
