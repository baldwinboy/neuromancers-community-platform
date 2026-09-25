"""Admin-authored peer application form page."""

from __future__ import annotations

from django.db import models
from modelcluster.fields import ParentalKey
from wagtail_daisIE.forms.fields import DaisieFormField
from wagtail_daisIE.forms.models import DaisieFormPage


class PeerApplicationFormField(DaisieFormField):
    page = ParentalKey(
        "peers.PeerApplicationFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class PeerApplicationFormPage(DaisieFormPage):
    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.peers.models import PeerApplication  # noqa: PLC0415

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        if PeerApplication.objects.filter(user=user).exists():
            return None

        data = form.cleaned_data
        return PeerApplication.objects.create(
            user=user,
            reason=data.get("reason", ""),
            submission=submission.form_data if submission is not None else {},
        )
