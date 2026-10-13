from allauth.account.forms import AddEmailForm as BaseAddEmailForm
from allauth.account.forms import SignupForm
from django import forms
from django.utils.translation import gettext_lazy as _

from neuromancers_network.moderation.identity import is_identity_blocked
from neuromancers_network.users.cooldown import ensure_email_change_allowed
from neuromancers_network.users.validators import validate_username_not_blocked


class UserSignupForm(SignupForm):
    """
    Form rendered on the user sign up screen.

    Default fields are added automatically from ``ACCOUNT_SIGNUP_FIELDS``.
    """

    accept_tos = forms.BooleanField(
        label=_("I accept the Terms and Conditions"),
        required=True,
    )

    def clean_username(self) -> str:
        username = super().clean_username()
        validate_username_not_blocked(username)
        if is_identity_blocked(username=username):
            raise forms.ValidationError(_("This username is not available."))
        return username

    def clean_email(self) -> str:
        email = super().clean_email()
        if is_identity_blocked(email=email):
            raise forms.ValidationError(
                _("This email address cannot be used to sign up."),
            )
        return email

    def save(self, request):
        user = super().save(request)
        user.accepted_tos = True
        user.save(update_fields=["accepted_tos"])
        return user


class AddEmailForm(BaseAddEmailForm):
    """allauth add-email form with an admin-configurable change cooldown."""

    def clean_email(self) -> str:
        value = super().clean_email()
        ensure_email_change_allowed(getattr(self, "user", None))
        return value
