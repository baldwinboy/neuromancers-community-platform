from django.utils.translation import gettext_lazy as _
from wagtail import blocks

from neuromancers_network.common.blocks.content import InlineBlock

from .base import ThemedBlock
from .base import ThemedTypographyBlock


class NavbarDesignBlock(ThemedBlock):
    default_link_design = ThemedTypographyBlock(
        required=False,
        label=_("Default link design"),
        help_text=_(
            "Typography settings for navbar links (except where overridden by the link design block below)",
        ),
    )

    class Meta:
        icon = "dots-horizontal"
        group = _("Navbar Design")
        collapsed = True


class NavbarDesignStreamBlock(blocks.StreamBlock):
    navbar_design = NavbarDesignBlock()

    class Meta:
        icon = "dots-horizontal"
        group = _("Navbar Design")
        collapsed = True


# --- ALLAUTH BLOCKS ---


class AllAuthFormBlock(blocks.StructBlock):
    """Collapsible block controlling labels and help texts for AllAuth forms."""

    login_heading = blocks.CharBlock(
        default="Sign In",
        help_text=_("Login page heading"),
    )
    login_subheading = blocks.CharBlock(
        required=False,
        default="",
        help_text=_("Subheading below the login heading"),
    )
    signup_heading = blocks.CharBlock(
        default="Create Account",
        help_text=_("Signup page heading"),
    )
    signup_subheading = blocks.CharBlock(
        required=False,
        default="",
        help_text=_("Subheading below the signup heading"),
    )
    username_label = blocks.CharBlock(default="Username")
    username_help = blocks.CharBlock(required=False, default="")
    email_label = blocks.CharBlock(default="Email")
    email_help = blocks.CharBlock(required=False, default="")
    password_label = blocks.CharBlock(default="Password")
    password_help = blocks.CharBlock(required=False, default="")
    login_button = blocks.CharBlock(default="Sign In")
    signup_button = blocks.CharBlock(default="Create Account")
    forgot_password_text = blocks.CharBlock(default="Forgot your password?")

    class Meta:
        icon = "form"
        group = _("AllAuth Form Labels")
        collapsed = True


class AllAuthFormStreamBlock(blocks.StreamBlock):
    allauth_form = AllAuthFormBlock()

    class Meta:
        icon = "form"
        group = _("AllAuth Form Labels")
        collapsed = True


class AllAuthDesignBlock(blocks.StructBlock):
    """
    Collapsible block controlling colors and typography for AllAuth forms.
    """

    default_form_design = InlineBlock(
        required=False,
        label=_("Default form design"),
        help_text=_(
            "Typography and color settings for form elements, except where overridden by the specific form element blocks below",
        ),
    )
    default_button_design = ThemedTypographyBlock(
        required=False,
        label=_("Default button design"),
        help_text=_(
            "Typography and color settings for buttons",
        ),
    )
    default_input_design = ThemedTypographyBlock(
        required=False,
        label=_("Default input design"),
        help_text=_(
            "Color and styling settings for form inputs (text fields, checkboxes, etc.)",
        ),
    )


class AllAuthDesignStreamBlock(blocks.StreamBlock):
    allauth_design = AllAuthDesignBlock()

    class Meta:
        icon = "form"
        group = _("AllAuth Form Design")
        collapsed = True
