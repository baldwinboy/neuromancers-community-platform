"""Inbox forms: flat checkbox opt-out lists for notification event types."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms import WagtailAdminModelForm

from neuromancers_network.inbox.models import NotificationEventType
from neuromancers_network.inbox.models import NotificationPreference


class EventTypeMultipleChoiceField(forms.MultipleChoiceField):
    """A flat checkbox list of notification event types.

    Used for opt-out lists, so it is optional and accepts an empty selection.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("choices", NotificationEventType.choices)
        kwargs.setdefault("widget", forms.CheckboxSelectMultiple)
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)


class NotificationPreferenceAdminForm(WagtailAdminModelForm):
    """Admin form editing the opt-out list as checkboxes, not raw JSON."""

    class Meta:
        model = NotificationPreference
        fields = ["user", "disabled_event_types"]

    disabled_event_types = EventTypeMultipleChoiceField(
        label=_("Disabled event types"),
        help_text=_("Event types this member has opted out of."),
    )
