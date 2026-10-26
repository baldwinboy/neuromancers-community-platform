import pytest
from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory

pytestmark = pytest.mark.django_db


class _SampleForm(forms.Form):
    name = forms.CharField()
    enabled = forms.BooleanField(required=False, help_text="Enable this option.")


def test_settings_section_uses_shared_form_renderer():
    request = RequestFactory().get("/settings/")
    html = render_to_string(
        "users/settings/_section.html",
        {"form": _SampleForm(), "key": "sample", "request": request},
        request=request,
    )

    assert "input w-full" in html
    assert 'class="checkbox"' in html
    assert "Enable this option." in html
