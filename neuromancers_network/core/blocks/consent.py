from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail_daisIE.base_blocks import DaisieStructBlock
from wagtail_daisIE.base_blocks import MainDesignBlock
from wagtail_daisIE.base_blocks import SpacedDesignBlock
from wagtail_daisIE.base_blocks import TypographyDesignBlock
from wagtail_daisIE.base_blocks.css import build_background_style
from wagtail_daisIE.base_blocks.css import build_design_css
from wagtail_daisIE.base_blocks.design import ButtonDesignBlock
from wagtail_daisIE.base_blocks.utils import build_class
from wagtail_daisIE.choices.feedback import TOAST_POSITION_CHOICES
from wagtail_daisIE.choices.inputs import CHOICE_COLOR_CHOICES
from wagtail_daisIE.choices.inputs import CHOICE_SIZE_CHOICES


class ConsentOptionDesignBlock(DaisieStructBlock):
    row = TypographyDesignBlock()
    color = blocks.ChoiceBlock(
        choices=CHOICE_COLOR_CHOICES,
        required=False,
        label=_("Checkbox colour"),
    )
    size = blocks.ChoiceBlock(
        choices=CHOICE_SIZE_CHOICES,
        required=False,
        label=_("Checkbox size"),
    )

    class Meta:
        icon = "tick-inverse"
        label = _("Checkbox option")
        form_layout = blocks.BlockGroup(
            children=["row", "color", "size"],
            heading=_("Checkbox option"),
        )


class ConsentCopyDesignBlock(DaisieStructBlock):
    title = TypographyDesignBlock()
    body = TypographyDesignBlock()

    class Meta:
        icon = "edit"
        label = _("Copy")
        form_layout = blocks.BlockGroup(
            children=["title", "body"],
            heading=_("Copy"),
        )


class ConsentOptionsDesignBlock(DaisieStructBlock):
    fieldset = SpacedDesignBlock()
    optional_legend = TypographyDesignBlock()
    necessary_legend = TypographyDesignBlock()
    option = ConsentOptionDesignBlock()
    necessary = ConsentOptionDesignBlock()

    class Meta:
        icon = "list-ul"
        label = _("Cookie options")
        form_layout = blocks.BlockGroup(
            children=[
                "fieldset",
                "optional_legend",
                "necessary_legend",
                "option",
                "necessary",
            ],
            heading=_("Cookie options"),
        )


class ConsentButtonsDesignBlock(DaisieStructBlock):
    row = SpacedDesignBlock()
    accept = ButtonDesignBlock()
    necessary = ButtonDesignBlock()

    class Meta:
        icon = "link"
        label = _("Banner buttons")
        form_layout = blocks.BlockGroup(
            children=["row", "accept", "necessary"],
            heading=_("Banner buttons"),
        )


class ConsentDesignBlock(DaisieStructBlock):
    banner = MainDesignBlock()
    banner_position = blocks.ChoiceBlock(
        choices=TOAST_POSITION_CHOICES,
        default="toast-center toast-bottom",
    )
    copy = ConsentCopyDesignBlock()
    form = SpacedDesignBlock()
    options = ConsentOptionsDesignBlock()
    buttons = ConsentButtonsDesignBlock()
    reopen_container = SpacedDesignBlock()
    reopen_button = ButtonDesignBlock()
    reopen_position = blocks.ChoiceBlock(
        choices=TOAST_POSITION_CHOICES,
        default="toast-end toast-bottom",
    )

    class Meta:
        icon = "sliders"
        label = _("Consent design")
        form_layout = blocks.BlockGroup(
            children=[
                blocks.BlockGroup(
                    children=["banner", "banner_position"],
                    heading=_("Banner"),
                ),
                blocks.BlockGroup(children=["copy"], heading=_("Copy")),
                blocks.BlockGroup(children=["form"], heading=_("Form")),
                blocks.BlockGroup(
                    children=["options"],
                    heading=_("Cookie options"),
                ),
                blocks.BlockGroup(
                    children=["buttons"],
                    heading=_("Banner buttons"),
                ),
                blocks.BlockGroup(
                    children=[
                        "reopen_container",
                        "reopen_button",
                        "reopen_position",
                    ],
                    heading=_("Cookie settings button"),
                ),
            ],
            heading=_("Design"),
        )


class ConsentSettingsDesignMixin:
    def get_design_value(self):
        if self.design:
            return self.design[0].value or {}
        return {}

    def get_design_child(self, *keys):
        value = self.get_design_value()
        for key in keys:
            value = (value or {}).get(key)
        return value

    @property
    def banner_position(self):
        return self.get_design_child("banner_position") or "toast-center toast-bottom"

    @property
    def banner_css(self):
        return build_class("alert", build_design_css(self.get_design_child("banner")))

    @property
    def banner_style(self):
        return build_background_style(self.get_design_child("banner"))

    @property
    def copy_title_css(self):
        return build_design_css(self.get_design_child("copy", "title"))

    @property
    def copy_title_style(self):
        return build_background_style(self.get_design_child("copy", "title"))

    @property
    def copy_body_css(self):
        return build_design_css(self.get_design_child("copy", "body"))

    @property
    def copy_body_style(self):
        return build_background_style(self.get_design_child("copy", "body"))

    @property
    def form_css(self):
        return build_design_css(self.get_design_child("form"))

    @property
    def form_style(self):
        return build_background_style(self.get_design_child("form"))

    @property
    def options_fieldset_css(self):
        return build_class(
            "fieldset w-full",
            build_design_css(self.get_design_child("options", "fieldset")),
        )

    @property
    def options_fieldset_style(self):
        return build_background_style(self.get_design_child("options", "fieldset"))

    @property
    def optional_legend_css(self):
        return build_design_css(
            self.get_design_child("options", "optional_legend"),
        )

    @property
    def optional_legend_style(self):
        return build_background_style(
            self.get_design_child("options", "optional_legend"),
        )

    @property
    def necessary_legend_css(self):
        return build_design_css(
            self.get_design_child("options", "necessary_legend"),
        )

    @property
    def necessary_legend_style(self):
        return build_background_style(
            self.get_design_child("options", "necessary_legend"),
        )

    @property
    def option_row_css(self):
        return build_design_css(self.get_design_child("options", "option", "row"))

    @property
    def option_row_style(self):
        return build_background_style(
            self.get_design_child("options", "option", "row"),
        )

    @property
    def option_color(self):
        return self.get_design_child("options", "option", "color") or ""

    @property
    def option_size(self):
        return self.get_design_child("options", "option", "size") or ""

    @property
    def necessary_row_css(self):
        return build_design_css(
            self.get_design_child("options", "necessary", "row"),
        )

    @property
    def necessary_row_style(self):
        return build_background_style(
            self.get_design_child("options", "necessary", "row"),
        )

    @property
    def necessary_color(self):
        return self.get_design_child("options", "necessary", "color") or ""

    @property
    def necessary_size(self):
        return self.get_design_child("options", "necessary", "size") or ""

    @property
    def buttons_row_css(self):
        return build_design_css(self.get_design_child("buttons", "row"))

    @property
    def buttons_row_style(self):
        return build_background_style(self.get_design_child("buttons", "row"))

    @property
    def accept_button_css(self):
        return build_design_css(self.get_design_child("buttons", "accept")) or "btn"

    @property
    def accept_button_style(self):
        return build_background_style(self.get_design_child("buttons", "accept"))

    @property
    def necessary_button_css(self):
        return build_design_css(self.get_design_child("buttons", "necessary")) or "btn"

    @property
    def necessary_button_style(self):
        return build_background_style(self.get_design_child("buttons", "necessary"))

    @property
    def reopen_position(self):
        return self.get_design_child("reopen_position") or "toast-end toast-bottom"

    @property
    def reopen_container_css(self):
        return build_design_css(self.get_design_child("reopen_container"))

    @property
    def reopen_container_style(self):
        return build_background_style(self.get_design_child("reopen_container"))

    @property
    def reopen_button_css(self):
        return build_design_css(self.get_design_child("reopen_button")) or "btn"

    @property
    def reopen_button_style(self):
        return build_background_style(self.get_design_child("reopen_button"))
