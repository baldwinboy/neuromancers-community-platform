"""Small htmx fragments for meeting form pages."""

from __future__ import annotations

from django.shortcuts import render

DEFAULT_TIER_FIELD_NAME = "duration_tiers"


def tier_row(request):
    """Return one blank duration/price row for the tier repeater."""
    name = request.GET.get("name") or DEFAULT_TIER_FIELD_NAME
    return render(request, "meetings/widgets/_tier_row.html", {"name": name})
