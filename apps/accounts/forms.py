import re

from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _, gettext_lazy as _lazy
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


class AccountSettingsForm(forms.ModelForm):
    """Form for changing core account fields: name, username, date of birth."""

    first_name = forms.CharField(
        required=True,
        label=_lazy("First name"),
        max_length=150,
        validators=[name_no_banned_words, name_safe_characters],
        widget=forms.TextInput(attrs={"placeholder": _lazy("First name")}),
    )
    last_name = forms.CharField(
        required=True,
        label=_lazy("Last name"),
        max_length=150,
        validators=[name_no_banned_words, name_safe_characters],
        widget=forms.TextInput(attrs={"placeholder": _lazy("Last name")}),
    )
    username = forms.CharField(
        required=True,
        label=_lazy("Username"),
        max_length=64,
        widget=forms.TextInput(attrs={"placeholder": _lazy("Username")}),
    )
    date_of_birth = forms.DateField(
        required=True,
        label=_lazy("Date of birth"),
        validators=[user_over_18],
        widget=forms.SelectDateWidget(years=current_birth_years),
    )

    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "username", "date_of_birth"]

    def clean_username(self):
        value = self.cleaned_data.get("username", "").lower()
        User = get_user_model()
        # Ensure uniqueness excluding the current user
        if User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise ValidationError(
                _("A user with that username already exists."),
                code="username_taken",
            )
        if re.match(username_banned_words_re, value):
            raise ValidationError(
                username_banned_words_message,
                code="signup_username_no_banned_words",
            )
        return value


MAX_UPLOAD_SIZE_MB = 2
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class ProfileForm(forms.ModelForm):
    """Form for editing user profile (access_needs for seekers, terms for hosts)"""

    display_picture_file = forms.FileField(
        required=False,
        label=_("Profile Picture"),
        widget=forms.FileInput(
            attrs={
                "class": "settings-avatar__input",
                "accept": "image/jpeg,image/png,image/gif,image/webp",
                "id": "id_display_picture_file",
            }
        ),
    )

    class Meta:
        from .models_users.profile import Profile

        model = Profile
        fields = [
            "about",
            "country",
            "access_needs",
            "terms_and_conditions",
        ]
        widgets = {
            "about": forms.Textarea(
                attrs={"rows": 4, "placeholder": _("Tell us about yourself...")}
            ),
            "access_needs": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": _(
                        "Describe any access needs Care Providers should know about..."
                    ),
                }
            ),
            "terms_and_conditions": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": _(
                        "Enter any terms Care Seekers must accept before requesting..."
                    ),
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        # Only show relevant fields based on user group
        if user:
            # Support seekers only see access_needs
            if user.groups.filter(name="SupportSeeker").exists():
                self.fields.pop("terms_and_conditions", None)
            # Peers only see terms_and_conditions
            elif user.has_perm("events.add_peersession"):
                self.fields.pop("access_needs", None)
            # Others see neither
            else:
                self.fields.pop("access_needs", None)
                self.fields.pop("terms_and_conditions", None)

    def clean_display_picture_file(self):
        f = self.cleaned_data.get("display_picture_file")
        if not f:
            return f

        # Validate content type
        content_type = getattr(f, "content_type", "")
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValidationError(
                _("Unsupported image type. Please upload a JPG, PNG, GIF or WebP."),
                code="invalid_image_type",
            )

        # Validate file size (2 MB max)
        if f.size > MAX_UPLOAD_SIZE_BYTES:
            raise ValidationError(
                _("File size must not exceed %(max)d MB.")
                % {"max": MAX_UPLOAD_SIZE_MB},
                code="file_too_large",
            )

        return f


class NotificationSettingsForm(forms.ModelForm):
    """Form for editing base notification settings (all users)"""

    class Meta:
        from .models_users.user_settings import NotificationSettings

        model = NotificationSettings
        exclude = ["user", "has_customized"]


class PeerNotificationSettingsForm(forms.ModelForm):
    """Form for editing peer-specific notification settings"""

    class Meta:
        from .models_users.user_settings import PeerNotificationSettings

        model = PeerNotificationSettings
        exclude = ["user", "has_customized"]


class PeerPrivacySettingsForm(forms.ModelForm):
    """Form for editing peer privacy settings (calendar visibility, etc.)"""

    class Meta:
        from .models_users.user_settings import PeerPrivacySettings

        model = PeerPrivacySettings
        exclude = ["user"]
        labels = {
            "show_calendar": _lazy("Show availability calendar"),
            "show_peer_session_details": _lazy("Show peer session details"),
            "show_group_session_details": _lazy("Show group session details"),
        }
