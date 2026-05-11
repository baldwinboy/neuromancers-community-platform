from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import BLANK_CHOICE_DASH
from django.utils.translation import gettext_lazy as _
from wagtail.blocks import BooleanBlock
from wagtail.blocks import CharBlock
from wagtail.blocks import ChoiceBlock
from wagtail.blocks import StreamBlock
from wagtail.blocks import StructBlock
from wagtail_link_block.blocks import LinkBlock

from .content import ContentBlock
from .form_fields import CharFieldBlock as BaseCharFieldBlock
from .form_fields import CheckboxesFieldBlock as BaseCheckboxesFieldBlock
from .form_fields import CheckboxFieldBlock as BaseCheckboxFieldBlock
from .form_fields import DateFieldBlock as BaseDateFieldBlock
from .form_fields import DateTimeFieldBlock as BaseDateTimeFieldBlock
from .form_fields import FileFieldBlock as BaseFileFieldBlock
from .form_fields import HiddenFieldBlock as BaseHiddenFieldBlock
from .form_fields import ImageFieldBlock as BaseImageFieldBlock
from .form_fields import NumberFieldBlock as BaseNumberFieldBlock
from .form_fields import OptionalFormFieldBlock
from .form_fields import RadioButtonsFieldBlock as BaseRadioButtonsFieldBlock
from .form_fields import TextFieldBlock as BaseTextFieldBlock
from .form_fields import TimeFieldBlock as BaseTimeFieldBlock

from neuromancers_network.common.binder import MODEL_ALLOWLISTS

MODEL_ACTION_MAP = {
    "create_session": {
        "label": _("Create Session"),
        "model": "events.session",
        "action": "create",
    },
    "edit_session": {
        "label": _("Edit Session"),
        "model": "events.session",
        "action": "update",
    },
    "delete_session": {
        "label": _("Delete Session"),
        "model": "events.session",
        "action": "delete",
    },
    "edit_profile": {
        "label": _("Edit Profile"),
        "model": "users.profile",
        "action": "update",
    },
}


class ModelMappableFieldBlock(OptionalFormFieldBlock):
    model_field = CharBlock(
        required=False,
        label=_("Map to model field"),
        help_text=_("Name of the field on the selected model (e.g. 'first_name')."),
    )

    class Meta:
        abstract = True


class CharFieldBlock(ModelMappableFieldBlock, BaseCharFieldBlock):
    class Meta:
        group = _("Text field (single line)")
        icon = "pilcrow"


class TextFieldBlock(ModelMappableFieldBlock, BaseTextFieldBlock):
    class Meta:
        group = _("Text field (multi line)")
        icon = "pilcrow"


class NumberFieldBlock(ModelMappableFieldBlock, BaseNumberFieldBlock):
    class Meta:
        group = _("Number field")
        icon = "decimal"


class CheckboxFieldBlock(ModelMappableFieldBlock, BaseCheckboxFieldBlock):
    class Meta:
        group = _("Checkbox field")
        icon = "tick-inverse"


class RadioButtonsFieldBlock(ModelMappableFieldBlock, BaseRadioButtonsFieldBlock):
    class Meta:
        group = _("Radio buttons")
        icon = "radio-empty"


class DropdownFieldBlock(RadioButtonsFieldBlock):
    widget = forms.Select

    class Meta:
        group = _("Dropdown field")
        icon = "list-ul"

    def get_field_kwargs(self, struct_value):
        kwargs = super().get_field_kwargs(struct_value)
        kwargs["choices"].insert(0, BLANK_CHOICE_DASH[0])
        return kwargs


class CheckboxesFieldBlock(ModelMappableFieldBlock, BaseCheckboxesFieldBlock):
    class Meta:
        group = _("Multiple checkboxes field")
        icon = "tasks"


class DateFieldBlock(ModelMappableFieldBlock, BaseDateFieldBlock):
    class Meta:
        group = _("Date field")
        icon = "date"


class TimeFieldBlock(ModelMappableFieldBlock, BaseTimeFieldBlock):
    class Meta:
        group = _("Time field")
        icon = "time"


class DateTimeFieldBlock(ModelMappableFieldBlock, BaseDateTimeFieldBlock):
    class Meta:
        group = _("Date+time field")
        icon = "date"


class ImageFieldBlock(ModelMappableFieldBlock, BaseImageFieldBlock):
    class Meta:
        group = _("Image field")
        icon = "image"


class FileFieldBlock(ModelMappableFieldBlock, BaseFileFieldBlock):
    class Meta:
        group = _("File field")
        icon = "upload"


class HiddenFieldBlock(ModelMappableFieldBlock, BaseHiddenFieldBlock):
    class Meta:
        group = _("Hidden field")
        icon = "no-view"


class ModelFormFieldsBlock(StreamBlock):
    char = CharFieldBlock(group=_("Fields"))
    text = TextFieldBlock(group=_("Fields"))
    number = NumberFieldBlock(group=_("Fields"))
    checkbox = CheckboxFieldBlock(group=_("Fields"))
    radios = RadioButtonsFieldBlock(group=_("Fields"))
    dropdown = DropdownFieldBlock(group=_("Fields"))
    checkboxes = CheckboxesFieldBlock(group=_("Fields"))
    date = DateFieldBlock(group=_("Fields"))
    time = TimeFieldBlock(group=_("Fields"))
    datetime = DateTimeFieldBlock(group=_("Fields"))
    image = ImageFieldBlock(group=_("Fields"))
    file = FileFieldBlock(group=_("Fields"))
    hidden = HiddenFieldBlock(group=_("Fields"))

    class Meta:
        group = _("Model form fields")
        min_num = 1


class ModelFormBlock(StructBlock):
    model_target = ChoiceBlock(
        choices=[(k, v["label"]) for k, v in MODEL_ACTION_MAP.items()],
        label=_("Model action"),
        help_text=_("Select the action to perform and the model to act on."),
    )
    form_fields = ModelFormFieldsBlock()
    to_email = CharBlock(
        required=False,
        label=_("Recipient email"),
        help_text=_("Email address to receive form submissions."),
    )
    success_url = LinkBlock(
        required=False,
        help_text=_("Redirect users to this page after successful submission."),
    )
    hide_on_success = BooleanBlock(
        required=False,
        default=False,
        help_text=_("Hide the form after a successful submission."),
    )
    success_content = ContentBlock(
        required=False,
        help_text=_(
            "Content to display after successful submission (used when no success URL is set).",
        ),
    )

    class Meta:
        icon = "form"
        group = _("Model Form")

    def clean(self, value):
        cleaned = super().clean(value)
        model_target = cleaned.get("model_target")
        form_fields = cleaned.get("form_fields", [])

        action_info = MODEL_ACTION_MAP.get(model_target) if model_target else None
        model_label = action_info["model"] if action_info else None
        allowed = MODEL_ALLOWLISTS.get(model_label, set()) if model_label else set()

        seen_fields = []
        for i, block_data in enumerate(form_fields):
            block_value = block_data.get("value", {})
            model_field = block_value.get("model_field", "")

            if model_field and not model_target:
                raise ValidationError(
                    _("Block %(index)d: field '%(field)s' is mapped but no model target is selected.")
                    % {"index": i + 1, "field": model_field},
                )

            if model_field and model_label and model_field not in allowed:
                raise ValidationError(
                    _("Block %(index)d: '%(field)s' is not a valid field for %(model)s.")
                    % {"index": i + 1, "field": model_field, "model": model_label},
                )

            if model_field and model_field in seen_fields:
                raise ValidationError(
                    _("Block %(index)d: field '%(field)s' is mapped more than once.")
                    % {"index": i + 1, "field": model_field},
                )

            if model_field:
                seen_fields.append(model_field)

        return cleaned


class ContentModelFormBlock(StreamBlock):
    form = ModelFormBlock()
    content = ContentBlock()

    class Meta:
        group = _("Content blocks")
        icon = "form"
        min_num = 1
