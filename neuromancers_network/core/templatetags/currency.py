"""Template filters for displaying localized money amounts."""

from __future__ import annotations

from django import template

from neuromancers_network.core.currency import format_amount

register = template.Library()


@register.filter
def money(amount, currency=None) -> str:
    """Format *amount* using babel, defaulting to the display currency."""
    if amount is None:
        return ""
    return format_amount(amount, currency=currency)
