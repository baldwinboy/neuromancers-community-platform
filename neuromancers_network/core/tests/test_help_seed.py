"""Smoke test for the Admin Guide seeder: data file loads, seeds and is
idempotent.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command

from neuromancers_network.core.models import HelpArticle
from neuromancers_network.core.models import HelpCategory

pytestmark = pytest.mark.django_db


def test_seed_help_guide_is_idempotent_and_renders_body():
    call_command("seed_help_guide")

    assert HelpCategory.objects.exists()
    article = HelpArticle.objects.filter(is_published=True).first()
    assert article is not None
    assert str(article.body).strip()

    article_count = HelpArticle.objects.count()
    category_count = HelpCategory.objects.count()

    call_command("seed_help_guide")

    assert HelpArticle.objects.count() == article_count
    assert HelpCategory.objects.count() == category_count
