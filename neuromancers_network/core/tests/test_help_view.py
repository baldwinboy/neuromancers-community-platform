"""Staff-only reader for the admin help guide."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from django.core.management import call_command
from django.urls import reverse

from neuromancers_network.core.models import GlossaryTerm
from neuromancers_network.core.models import HelpArticle
from neuromancers_network.core.models import HelpCategory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(client):
    client.force_login(UserFactory(is_superuser=True))
    return client


def test_help_guide_is_staff_only(client):
    response = client.get(reverse("help_guide"))

    assert response.status_code != HTTPStatus.OK


def test_help_guide_renders_published_articles_and_glossary(staff_client):
    category = HelpCategory.objects.create(name="Administrators", sort_order=1)
    HelpArticle.objects.create(
        title="Your admin role",
        category=category,
        is_published=True,
        summary="Where to find everything.",
    )
    HelpArticle.objects.create(
        title="Unpublished draft",
        category=category,
        is_published=False,
    )
    GlossaryTerm.objects.create(term="Stripe", definition="The payments provider.")

    response = staff_client.get(reverse("help_guide"))

    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert "Your admin role" in content
    assert "Where to find everything." in content
    assert "Unpublished draft" not in content
    assert "Stripe" in content


def test_help_guide_renders_table_blocks(staff_client):
    call_command("seed_help_guide")

    response = staff_client.get(reverse("help_guide"))

    content = response.content.decode()
    assert response.status_code == HTTPStatus.OK
    assert "Merchant of record" in content
    assert "Host link" in content
