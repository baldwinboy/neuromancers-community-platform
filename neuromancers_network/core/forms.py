from __future__ import annotations

from typing import cast

from django import forms
from django.utils.translation import gettext_lazy as _

from neuromancers_network.payments.services import DEFAULT_WEBHOOK_EVENTS


class StripeWebhookForm(forms.Form):
    """Form for creating the platform Stripe webhook endpoint."""

    webhook_uuid = forms.UUIDField(widget=forms.HiddenInput)
    url = forms.URLField(label=_("Endpoint URL"))
    enabled_events = forms.MultipleChoiceField(
        label=_("Events"),
        widget=forms.CheckboxSelectMultiple,
        choices=[],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = cast("forms.MultipleChoiceField", self.fields["enabled_events"])
        field.choices = [(event, event) for event in DEFAULT_WEBHOOK_EVENTS]


class SendTestEmailForm(forms.Form):
    """Form for sending a test email through the configured backend."""

    email = forms.EmailField(label=_("Recipient"))
