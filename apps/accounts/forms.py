import re

from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .utils import current_birth_years
from .validators import (
    name_no_banned_words,
    name_safe_characters,
    user_over_18,
    username_banned_words_message,
    username_banned_words_re,
)


class SignupForm(AllauthSignupForm):
    first_name = forms.CharField(
        required=True,
        label=_("First name"),
        max_length=150,
        validators=[name_no_banned_words, name_safe_characters],
        widget=forms.TextInput(attrs={"placeholder": _("First name")}),
    )
    last_name = forms.CharField(
        required=True,
        label=_("Last name"),
        max_length=150,
        validators=[name_no_banned_words, name_safe_characters],
        widget=forms.TextInput(attrs={"placeholder": _("Last name")}),
    )
    date_of_birth = forms.DateField(
        required=True,
        label=_("Date of birth"),
        validators=[user_over_18],
        widget=forms.SelectDateWidget(years=current_birth_years),
    )

    field_order = [
        "first_name",
        "last_name",
        "date_of_birth",
        "username",
        "email",
        "email2",
        "password1",
        "password2",
    ]

    def clean_username(self):
        value = super().clean_username()
        # Force usernames to be lowercase
        value = value.lower()
        # Check for banned words
        if re.match(username_banned_words_re, value):
            raise ValidationError(
                username_banned_words_message, code="signup_username_no_banned_words"
            )

        return value

    def save(self, request):
        user = super(SignupForm, self).save(request)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.date_of_birth = self.cleaned_data["date_of_birth"]
        user.save()
        return user
