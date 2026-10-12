from allauth.account.forms import SignupForm
from django import forms
from django.utils.translation import gettext_lazy as _

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
        return username

    def save(self, request):
        user = super().save(request)
        user.accepted_tos = True
        user.save(update_fields=["accepted_tos"])
        return user
