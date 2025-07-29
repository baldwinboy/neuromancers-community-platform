from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms
from django.utils.translation import gettext as _

from .validators import username_no_banned_words, username_safe_characters


class SignupForm(AllauthSignupForm):
    first_name = forms.CharField(
        required=True,
        label=_("First name"),
        max_length=150,
        validators=[username_no_banned_words, username_safe_characters],
        widget=forms.TextInput(attrs={"placeholder": _("First name")}),
    )
    last_name = forms.CharField(
        required=True,
        label=_("Last name"),
        max_length=150,
        validators=[username_no_banned_words, username_safe_characters],
        widget=forms.TextInput(attrs={"placeholder": _("Last name")}),
    )

    field_order = [
        "first_name",
        "last_name",
        "username",
        "email",
        "email2",
        "password1",
        "password2",
    ]

    def save(self, request):
        user = super(SignupForm, self).save(request)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()
        return user
