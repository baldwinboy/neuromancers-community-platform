from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.http import Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.test import RequestFactory
from wagtail.models import get_page_models
from wagtail_daisIE.detail_pages.models import GeneratedPagesIndexPage
from wagtail_daisIE.detail_pages.models import ModelDetailTemplate

PROJECT_MODULE = "neuromancers_network."

pytestmark = pytest.mark.django_db


def _project_page_models():
    return [
        cls for cls in get_page_models() if cls.__module__.startswith(PROJECT_MODULE)
    ]


def test_all_project_page_models_have_resolvable_templates():
    missing = []

    for cls in _project_page_models():
        try:
            get_template(cls.template)
        except TemplateDoesNotExist:
            missing.append(f"{cls.__name__} -> {cls.template}")

    assert not missing, "Missing page templates:\n" + "\n".join(missing)


def test_non_navigable_pages_remain_non_navigable():
    request = RequestFactory().get("/")

    for cls in _project_page_models():
        if not issubclass(cls, (GeneratedPagesIndexPage, ModelDetailTemplate)):
            continue

        page = cls()
        assert page.get_url_parts() is None
        with pytest.raises(Http404):
            page.serve(request)


def test_project_template_includes_resolve():
    template_root = Path(settings.APPS_DIR) / "templates"
    pattern = re.compile(
        r'{%\s*(?:extends|include)\s+["\']([^"\']+\.html)["\']',
    )
    missing = []

    for path in template_root.rglob("*.html"):
        text = path.read_text()
        for match in pattern.finditer(text):
            name = match.group(1)
            try:
                get_template(name)
            except TemplateDoesNotExist:
                missing.append(f"{name} referenced by {path}")

    assert not missing, "Missing template references:\n" + "\n".join(missing)
