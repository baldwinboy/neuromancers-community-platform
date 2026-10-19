"""Smoke test for the Admin Guide seeder: data file loads, seeds and is
idempotent.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command

from neuromancers_network.core.help_seed import load_help_spec
from neuromancers_network.core.models import HelpArticle
from neuromancers_network.core.models import HelpCategory

pytestmark = pytest.mark.django_db

MAX_SLUG_LENGTH = 50


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


def test_identity_articles_exist_and_getpronto_is_not_a_video_provider():
    spec = load_help_spec()
    articles = {article["slug"]: article for article in spec["articles"]}

    assert "requests-bookings-and-sessions" in articles
    assert "provider-overview-whereby-daily-getpronto-stripe" in articles

    video = articles["video-providers-whereby-getpronto-daily"]
    body = " ".join(entry["value"]["text"] for entry in video["body"])
    assert "not a video provider" in body


def test_every_seeded_article_is_consistent():
    spec = load_help_spec()

    categories = {category["slug"] for category in spec["categories"]}
    assert spec["articles"]
    assert all(article["category"] in categories for article in spec["articles"])
    assert all(len(article["slug"]) <= MAX_SLUG_LENGTH for article in spec["articles"])


def test_comparison_tables_are_seeded():
    spec = load_help_spec()
    articles = {article["slug"]: article for article in spec["articles"]}

    stripe_tables = [
        entry
        for entry in articles["configuring-stripe-and-payouts"]["body"]
        if entry["type"] == "table"
    ]
    provider_tables = [
        entry
        for entry in articles["provider-overview-whereby-daily-getpronto-stripe"][
            "body"
        ]
        if entry["type"] == "table"
    ]

    assert stripe_tables[0]["value"]["content"]["data"][1][0] == "Direct"
    provider_rows = provider_tables[0]["value"]["content"]["data"]
    assert "Whereby" in provider_rows[1]
    assert "Daily" in provider_rows[2]
