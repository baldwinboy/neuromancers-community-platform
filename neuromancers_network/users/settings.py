"""App-owned settings sections loaded into an admin-authored Settings page.

The Wagtail admin authors the page shell (``TabsBlock`` + ``ActionFormBlock``);
each ``settings.*`` action is intercepted by a project template override and
htmx-loads the matching section form from here. Forms own validation and
persistence; the plugin owns tabs, icons, audience gating and the ``?tab=``
state.
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import render
from django.urls import path
from django.utils.translation import gettext_lazy as _
from wagtail_daisIE.widgets import DaisieAutocompleteSelectMultiple

from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.inbox.forms import EventTypeMultipleChoiceField
from neuromancers_network.inbox.models import NotificationPreference
from neuromancers_network.taxonomy.models import Country
from neuromancers_network.taxonomy.models import Language
from neuromancers_network.users.cooldown import ensure_username_change_allowed
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.services import record_username_change
from neuromancers_network.users.utils import normalize_username
from neuromancers_network.users.validators import validate_username_not_blocked

User = get_user_model()

_NOTIFY_FIELDS = (
    "notify_meeting_request",
    "notify_meeting_approved",
    "notify_meeting_reminder",
    "notify_review_received",
    "notify_refund_request",
    "notify_peer_application_update",
    "notify_platform_announcements",
)


def profile_for(user) -> UserProfile:
    profile, _created = UserProfile.objects.get_or_create(user=user)
    return profile


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("name", "username", "date_of_birth")
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_username = self.instance.username

    def clean_username(self):
        value = normalize_username(self.cleaned_data["username"])
        if (
            User.objects.filter(username__iexact=value)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(_("A user with that username already exists."))
        validate_username_not_blocked(value)
        if value != self._original_username:
            ensure_username_change_allowed(self.instance)
        return value

    def save(self, commit=True):  # noqa: FBT002 - required ModelForm signature
        user = super().save(commit=commit)
        new_username = self.cleaned_data.get("username")
        if commit and new_username and new_username != self._original_username:
            record_username_change(user, self._original_username)
        return user


class ProfileForm(forms.ModelForm):
    country = forms.ChoiceField(required=False, label=_("Country"))
    languages = forms.ModelMultipleChoiceField(
        queryset=Language.objects.none(),
        required=False,
        label=_("Languages"),
        widget=DaisieAutocompleteSelectMultiple(placeholder=_("Languages")),
    )

    class Meta:
        model = UserProfile
        fields = ("bio", "access_needs", "country", "timezone", "languages")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].choices = [("", _("Not set"))] + [
            (country.code, country.name) for country in Country.objects.all()
        ]
        self.fields["languages"].queryset = Language.objects.filter(is_active=True)


class PrivacyForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("visibility", "access_needs_visible_to_peer")


class NotificationForm(forms.Form):
    disabled_event_types = EventTypeMultipleChoiceField(
        label=_("Notifications to turn off"),
    )

    def __init__(self, *args, profile=None, **kwargs):
        self.profile = profile
        initial = kwargs.setdefault("initial", {})
        if profile is not None:
            for field in _NOTIFY_FIELDS:
                initial.setdefault(field, getattr(profile, field))
            preference = getattr(profile.user, "notification_preference", None)
            initial.setdefault(
                "disabled_event_types",
                list(preference.disabled_event_types) if preference else [],
            )
        super().__init__(*args, **kwargs)
        for field in _NOTIFY_FIELDS:
            self.fields[field] = forms.BooleanField(
                required=False,
                initial=initial.get(field, True),
                label=UserProfile._meta.get_field(field).verbose_name,  # noqa: SLF001
            )

    def save(self):
        for field in _NOTIFY_FIELDS:
            setattr(self.profile, field, self.cleaned_data[field])
        self.profile.save()
        preference, _created = NotificationPreference.objects.get_or_create(
            user=self.profile.user,
        )
        preference.disabled_event_types = list(
            self.cleaned_data["disabled_event_types"],
        )
        preference.save()


def _account_form(user, data=None, files=None):
    return AccountForm(data, files, instance=user)


def _profile_form(user, data=None, files=None):
    return ProfileForm(data, files, instance=profile_for(user))


def _privacy_form(user, data=None, files=None):
    return PrivacyForm(data, files, instance=profile_for(user))


def _notification_form(user, data=None, files=None):
    return NotificationForm(data, files, profile=profile_for(user))


#: action key -> form factory ``(user, data, files) -> Form``.
SECTIONS = {
    "settings.account": _account_form,
    "settings.profile": _profile_form,
    "settings.privacy": _privacy_form,
    "settings.notifications": _notification_form,
}


def settings_section(request, key):
    """Render and save one settings section (htmx fragment or full page)."""
    user = require_authenticated(request)
    factory = SECTIONS.get(key)
    if factory is None:
        raise Http404

    if request.method == "POST":
        form = factory(user, request.POST, request.FILES)
        if form.is_valid():
            form.save()
            if getattr(request, "htmx", False):
                return render(
                    request,
                    "users/settings/_section.html",
                    {"form": factory(user), "key": key, "saved": True},
                )
            messages.success(request, _("Your settings have been saved."))
            return redirect_back(request)
    else:
        form = factory(user)

    return render(
        request,
        "users/settings/_section.html",
        {"form": form, "key": key},
    )


def action_handler(request, data):
    """daisIE action entry point (non-htmx fallback for ``settings.*``)."""
    key = (
        request.resolver_match.kwargs.get("action_key", "")
        if request.resolver_match
        else ""
    )
    return settings_section(request, key)


app_name = "settings"

urlpatterns = [
    path("<str:key>/", settings_section, name="section"),
]
