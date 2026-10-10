import json
from typing import override

from django import forms
from wagtail.admin.forms.models import WagtailAdminModelForm

from neuromancers_network.meetings.models.choices import MeetingType
from neuromancers_network.meetings.models.choices import PricingType
from neuromancers_network.taxonomy.forms import AllowedTagsCountriesFormMixin


class PricingTypeSelect(forms.Select):
    @override
    def create_option(
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
        if value == PricingType.DURATION_TIERS:
            option["attrs"].update(
                {
                    "data-w-rules-target": "show",
                    "data-w-rules": json.dumps({"meeting_type": ["1:1"]}),
                },
            )
        return option


class MeetingAdminForm(AllowedTagsCountriesFormMixin, WagtailAdminModelForm):
    """Admin form enforcing that meeting tags/countries are allowed.

    Also keeps the two meeting modes coherent. ``max_participants`` is a
    group-only setting, so any value retained on the hidden field is discarded
    for 1:1 meetings; and duration tiers are removed from group meetings on
    save. Panel and ``pricing_type`` visibility is driven client-side by the
    ``meeting-type`` Stimulus controller, with the model's own validation as
    the authoritative fallback.
    """

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("meeting_type") == MeetingType.ONE_ON_ONE
            and "max_participants" in cleaned_data
        ):
            cleaned_data["max_participants"] = None
        return cleaned_data

    def save(self, commit=True):  # noqa: FBT002
        meeting = super().save(commit=commit)
        if commit and meeting.meeting_type == MeetingType.GROUP:
            meeting.price_tiers.all().delete()
        return meeting
