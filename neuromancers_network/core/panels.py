"""Custom Wagtail admin panels and widgets."""

from __future__ import annotations

import json

from django import forms
from django.conf import settings
from django.urls import reverse
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import Panel
from wagtail.admin.ui.components import Component


def stripe_price_choices() -> list[tuple[str, str]]:
    """Return ``(price_id, label)`` pairs from dj-stripe, or an empty list."""
    try:
        from djstripe.models import Price  # noqa: PLC0415

        return [(price.id, str(price)) for price in Price.objects.all()[:500]]
    except Exception:  # noqa: BLE001 - dj-stripe may be unavailable
        return []


class StripePriceChooserWidget(forms.CheckboxSelectMultiple):
    """A multi-select of Stripe Prices that round-trips a JSON list."""

    def optgroups(self, name, value, attrs=None):
        self.choices = stripe_price_choices()
        return super().optgroups(name, value, attrs)

    def value_from_datadict(self, data, files, name):
        values = super().value_from_datadict(data, files, name)
        if values is None:
            return None
        return json.dumps(list(values))

    def format_value(self, value):
        if not value:
            return []
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except TypeError, ValueError:
                return []
        return value or []


class StripePriceChooserPanel(FieldPanel):
    """Field panel for a JSON list of Stripe Price IDs."""

    def __init__(self, field_name, **kwargs):
        kwargs.setdefault("widget", StripePriceChooserWidget)
        super().__init__(field_name, **kwargs)


class StripeOpsPanel(Panel):
    """Read-only panel with links to Stripe operational views."""

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtailadmin/panels/stripe_ops.html"


class SendTestEmailPanel(Panel):
    """Panel with a form to send a test email through the configured backend."""

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtailadmin/panels/send_test_email.html"


class HelpGuidePanel(Component):
    """Dashboard panel linking to the staff-only admin help guide."""

    name = "help_guide"
    order = 150
    template_name = "core/help_panel.html"

    def get_context_data(self, parent_context):
        return {"help_url": reverse("help_guide")}


class DemoDataPanel(Component):
    """Dashboard panel linking to the demo/test data administration view."""

    name = "demo_data"
    order = 160
    template_name = "core/demo_data_panel.html"

    def get_context_data(self, parent_context):
        return {
            "demo_url": reverse("demo_data"),
            "demo_enabled": settings.DEMO_DATA_ENABLED,
        }
