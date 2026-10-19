"""Shared form-page block configuration.

All admin-authored form pages use this base so the padded form-field wrapper is
available everywhere, without changing the package-level ``FormContentBlock``.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.fields import StreamField
from wagtail_daisIE.base_blocks import ThemedBlock
from wagtail_daisIE.blocks.content import ALL_CONTENT_BLOCKS
from wagtail_daisIE.forms.blocks import FormContentBlock
from wagtail_daisIE.forms.blocks import FormFieldBlock
from wagtail_daisIE.forms.models import DaisieFormPage

FORM_FIELD_BLOCK_TYPE = "form_field"
FORM_FIELD_WRAPPER_BLOCK_TYPE = "form_field_wrapper"


class FormFieldWrapperBlock(ThemedBlock):
    """Wrap one bound form field in an admin-designed container."""

    field = FormFieldBlock()

    class Meta:
        icon = "form"
        label = _("Form field (padded)")
        template = "core/blocks/form_field_wrapper.html"
        form_layout = blocks.BlockGroup(
            children=["field"],
            settings=["design"],
        )

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        # ThemedBlock does not copy ``form``; the nested FormFieldBlock needs it
        # to resolve the bound field during rendering.
        context["form"] = (parent_context or {}).get("form")
        return context


class ProjectFormContentBlock(FormContentBlock):
    """Form body that accepts both plain and padded bound fields."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "local_blocks",
            [
                *ALL_CONTENT_BLOCKS,
                (FORM_FIELD_BLOCK_TYPE, FormFieldBlock()),
                (FORM_FIELD_WRAPPER_BLOCK_TYPE, FormFieldWrapperBlock()),
            ],
        )
        super().__init__(*args, **kwargs)


class ProjectDaisieFormPage(DaisieFormPage):
    """Common base for project form pages with padded field wrappers."""

    body = StreamField(
        ProjectFormContentBlock(),
        blank=True,
        use_json_field=True,
        verbose_name=_("Body"),
        help_text=_(
            "Add content blocks and place the form's fields in any order. Fields "
            "that are not placed here are shown above the submit button.",
        ),
    )

    class Meta:
        abstract = True

    def get_placed_field_names(self):
        names = []
        for child in self.body:
            if child.block_type == FORM_FIELD_BLOCK_TYPE and child.value:
                names.append(child.value)
            elif child.block_type == FORM_FIELD_WRAPPER_BLOCK_TYPE:
                name = (child.value or {}).get("field")
                if name:
                    names.append(name)
        return names

    def clean(self):
        super().clean()
        seen = set()
        duplicates = []
        for name in self.get_placed_field_names():
            if name in seen and name not in duplicates:
                duplicates.append(name)
            seen.add(name)
        if duplicates:
            message = _(
                "These form fields are placed more than once: %(names)s",
            ) % {"names": ", ".join(duplicates)}
            raise ValidationError({"body": message})
