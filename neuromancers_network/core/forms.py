from __future__ import annotations

from typing import cast

from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms import WagtailAdminModelForm

from neuromancers_network.core.models import NotificationSettings
from neuromancers_network.core.utils import ALL_AUDIENCE
from neuromancers_network.core.utils import audience_choices
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


class AudienceSelectMultiple(forms.CheckboxSelectMultiple):
    """Checkbox list wired to Wagtail's ``w-bulk`` controller."""

    def create_option(  # noqa: PLR0913, PLR0917
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex,
            attrs,
        )
        if value == ALL_AUDIENCE:
            option["attrs"]["data-action"] = "w-bulk#toggleAll"
            option["attrs"]["data-w-bulk-target"] = "all"
        else:
            option["attrs"]["data-action"] = "w-bulk#toggle"
            option["attrs"]["data-w-bulk-target"] = "item"
        return option


class ResetTosForm(forms.Form):
    audiences = forms.MultipleChoiceField(
        label=_("Audiences"),
        choices=(),
        widget=AudienceSelectMultiple,
    )
    confirm = forms.BooleanField(
        label=_("I understand this clears the acceptance flag for the audience."),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["audiences"].choices = audience_choices()

    def clean_audiences(self) -> list[str]:
        """Collapse "all" (explicit, or implied by selecting every audience)."""
        selected = self.cleaned_data["audiences"]
        if ALL_AUDIENCE in selected:
            return [ALL_AUDIENCE]
        individuals = {key for key, _label in audience_choices() if key != ALL_AUDIENCE}
        if individuals and set(selected) == individuals:
            return [ALL_AUDIENCE]
        return selected


class NotificationSettingsForm(WagtailAdminModelForm):
    """Admin form editing the notification defaults as checkbox lists."""

    class Meta:
        model = NotificationSettings
        fields = [
            "default_disabled_event_types",
            "transactional_events",
        ]

    def __init__(self, *args, **kwargs):
        # Imported lazily: the field lives with the inbox app to avoid a
        # core.models <-> inbox.models import cycle.
        from neuromancers_network.inbox.forms import (  # noqa: PLC0415
            EventTypeMultipleChoiceField,
        )

        super().__init__(*args, **kwargs)
        self.fields["default_disabled_event_types"] = EventTypeMultipleChoiceField(
            label=_("Default disabled event types"),
            help_text=_("Event types disabled for members unless they opt back in."),
        )
        self.fields["transactional_events"] = EventTypeMultipleChoiceField(
            label=_("Transactional event types"),
            help_text=_(
                "Event types that can never be opted out of, in addition to the "
                "platform's fixed transactional events.",
            ),
        )
