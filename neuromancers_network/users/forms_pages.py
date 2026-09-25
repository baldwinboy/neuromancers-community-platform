"""Admin-authored member profile edit form page."""

from __future__ import annotations

from django.db import models
from modelcluster.fields import ParentalKey
from wagtail_daisIE.forms.fields import DaisieFormField
from wagtail_daisIE.forms.models import DaisieFormPage

_PROFILE_FIELDS = ("access_needs", "visibility", "timezone", "country")


def _as_list(value) -> list:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [item.strip() for item in str(value).split(",") if item.strip()]


class ProfileEditFormField(DaisieFormField):
    page = ParentalKey(
        "users.ProfileEditFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class ProfileEditFormPage(DaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.users.models import UserProfile  # noqa: PLC0415

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        data = form.cleaned_data
        profile, _created = UserProfile.objects.get_or_create(user=user)
        for field_name in _PROFILE_FIELDS:
            if field_name in data:
                setattr(profile, field_name, data[field_name])
        profile.save()
        if "languages" in data:
            profile.languages.set(_as_list(data["languages"]))
        return profile
