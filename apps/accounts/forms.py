import re

from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from wagtail.contrib.settings.registry import registry

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
    accept_toc = forms.BooleanField()

    field_order = [
        "first_name",
        "last_name",
        "date_of_birth",
        "username",
        "email",
        "email2",
        "password1",
        "password2",
        "accept_toc",
    ]

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        terms_and_conditions = (
            registry.get_by_natural_key("core", "Links")
            .load(request)
            .terms_and_conditions
        )
        label_template = _(
            'I have read and agree to the <a href="%(url)s" target="_blank" rel="noopener">'
            "Terms and Conditions</a>"
        )
        # Interpolate URL *after* translation, then mark as safe for HTML
        label = mark_safe(label_template % {"url": terms_and_conditions})

        self.fields["accept_toc"].label = label

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

    def clean_accept_toc(self):
        value = self.cleaned_data.get("accept_toc")

        if not value:
            raise ValidationError(
                _(
                    "You must accept the terms and conditions in order to use this platform"
                ),
                code="accept_toc",
            )

        return value

    def save(self, request):
        user = super(SignupForm, self).save(request)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.date_of_birth = self.cleaned_data["date_of_birth"]
        user.accept_toc = self.cleaned_data["accept_toc"]
        user.save()
        return user
