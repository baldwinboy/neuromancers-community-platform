import logging

from django import forms
from django.utils.translation import gettext as _
from wagtail.contrib.settings.registry import registry
from wagtail.fields import StreamValue

logger = logging.getLogger(__name__)


class GroupedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """
    A CheckboxSelectMultiple that supports grouped choices.
    Choices format:
    [
        (('group_a', 'Group A'), [('value1', 'Label 1'), ('value2', 'Label 2')]),
        (('group_b', 'Group B'), [('value3', 'Label 3')]),
    ]
    """

    template_name = "forms/widgets/grouped_checkbox_select.html"

    def optgroups(self, name, value, attrs=None):
        """
        Generate grouped choices in the format:
        ((group_value, group_label), [(option_value, option_label), ...])
        """
        if value is None:
            value = []
        value = set(str(v) for v in value)

        groups = []
        option_index = 0  # used to generate unique IDs per option

        for group, options in self.choices:
            group_value, group_label = group
            subgroup = []
            for option_value, option_label in options:
                widget = forms.CheckboxInput(
                    attrs=attrs, check_test=lambda v: str(v) in value
                )
                # Pass index to generate unique ID
                option_tag = widget.render(
                    name,
                    option_value,
                    attrs={"id": f"id_{name}_{group_value}_{option_index}"},
                )
                option_index += 1
                subgroup.append(
                    {
                        "tag": option_tag,
                        "label": option_label,
                        "id": f"id_{name}_{option_index - 1}",  # label "for" attribute
                    }
                )
            groups.append((group_label, subgroup, group_value))
        return groups


class FiltersMultipleChoiceField(forms.MultipleChoiceField):
    """
    A MultipleChoice field that populates its choices from
    FilterSettings.filters
    """

    def __init__(self, request=None, **kwargs):
        kwargs.setdefault("choices", [])  # empty for now
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.HiddenInput)
        super().__init__(**kwargs)
        self.request = request

    def prepare_value(self, value):
        """
        Convert stored JSON of selected filters into the list of
        'group::item' strings expected by the checkbox widget.
        """
        if not value:
            return []

        # If value is already the checkbox list format, return it
        if isinstance(value, (list, tuple)):
            return value

        prepared = []

        # Normalized form: { group_slug: { items: { item_slug: {...} } } }
        for group_slug, group_data in value.items():
            items = group_data.get("items", {})
            for item_slug in items.keys():
                prepared.append(f"{group_slug}::{item_slug}")

        return prepared

    def clean(self, value):
        # Normal MultipleChoice validation
        value = super().clean(value)

        # Must have normalized mapping from load_from_request()
        if not hasattr(self, "normalized"):
            raise RuntimeError(
                "FiltersMultipleChoiceField.clean() called before load_from_request()."
            )

        normalized = self.normalized

        output = {}  # final JSON structure

        for v in value:
            try:
                group_slug, item_slug = v.split("::", 1)
            except ValueError:
                continue  # skip invalid values

            group = normalized.get(group_slug)
            if not group:
                continue

            # Ensure group object exists
            if group_slug not in output:
                output[group_slug] = {
                    "slug": group_slug,
                    "label": group["label"],
                    "items": {},
                }

            item = group["items"].get(item_slug)
            if item:
                output[group_slug]["items"][item_slug] = item

        return output

    def load_from_request(self, request):
        self.request = request
        # Load registry object
        filter_settings = registry.get_by_natural_key("events", "FilterSettings").load(
            request
        )
        filters = filter_settings.filters
        if isinstance(filters, StreamValue):
            self.normalized = filter_settings.get_cached_mapping()

            choices = []
            flat_choices = []

            for group_slug, group in self.normalized.items():
                group_label = _(group["label"])
                subgroup = [
                    (f"{group_slug}::{item_slug}", _(item["label"]))
                    for item_slug, item in group["items"].items()
                ]

                choices.append(((group_slug, _(group_label)), subgroup))
                flat_choices.extend(subgroup)

            if choices:
                self.choices = flat_choices
                self.widget = GroupedCheckboxSelectMultiple(choices=choices)


class WagtailAdminFiltersMultipleChoiceField(GroupedCheckboxSelectMultiple):
    """
    A custom widget that renders filters as grouped checkboxes in Wagtail admin.
    """

    template_name = "wagtailadmin/widgets/grouped_checkbox_select.html"

    def __init__(self, attrs=None, choices=[]):
        # Load registry object
        super().__init__(attrs, choices)  # initialize with empty choices
        try:
            filter_settings = registry.get_by_natural_key(
                "events", "FilterSettings"
            ).load()
        except Exception:
            # Table may not exist yet during migrations or DB reset
            logger.debug(
                "FilterSettings table not available yet, skipping filter loading."
            )
            return
        filters = filter_settings.filters
        if isinstance(filters, StreamValue):
            self.normalized = filter_settings.get_cached_mapping()

            choices = []
            flat_choices = []

            for group_slug, group in self.normalized.items():
                group_label = _(group["label"])
                subgroup = [
                    (f"{group_slug}::{item_slug}", _(item["label"]))
                    for item_slug, item in group["items"].items()
                ]

                choices.append(((group_slug, _(group_label)), subgroup))
                flat_choices.extend(subgroup)

            if choices:
                self.choices = choices

    def format_value(self, value):
        """
        Format the value for display in the widget.
        Converts stored JSON into list of 'group::item' strings.
        """
        if not value:
            return []

        # If value is already the checkbox list format, return it
        if isinstance(value, (list, tuple)):
            return value

        if isinstance(value, str):
            # Attempt to parse JSON string if value is a string
            import json

            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return []

        if not isinstance(value, dict):
            return []

        prepared = []

        # Normalized form: { group_slug: { items: { item_slug: {...} } } }
        for group_slug, group_data in value.items():
            items = group_data.get("items", {})
            for item_slug in items.keys():
                prepared.append(f"{group_slug}::{item_slug}")

        return prepared

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        return context
