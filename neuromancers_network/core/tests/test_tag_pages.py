from __future__ import annotations

import pytest
from django.test import RequestFactory
from wagtail.models import Page

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import StandardPage
from neuromancers_network.core.models.pages import TagDetailPage
from neuromancers_network.core.models.pages import TagIndexPage
from neuromancers_network.taxonomy.tests.factories import AllowedTagFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tag_index() -> TagIndexPage:
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="Home", slug="home")
        root.add_child(instance=home)
    index = home.get_children().filter(slug="tags").first()
    if index is None:
        index = TagIndexPage(title="Tags", slug="tags")
        home.add_child(instance=index)
        index.save_revision().publish()
    return index.specific


class TestTagDetailPages:
    def test_page_created_for_active_tag(self, tag_index):
        tag = AllowedTagFactory(name="anxiety", is_active=True)

        page = TagDetailPage.objects.filter(
            detail_key="tag",
            source_object_id=tag.pk,
        ).first()

        assert page is not None
        assert page.live is True
        assert page.title == "anxiety"

    def test_page_deleted_with_tag(self, tag_index):
        tag = AllowedTagFactory(name="grief")
        assert TagDetailPage.objects.filter(source_object_id=tag.pk).exists()

        tag.delete()

        assert not TagDetailPage.objects.filter(source_object_id=tag.pk).exists()


class TestTagDetailContext:
    def test_tagged_pages_lists_pages_with_tag(self, tag_index):
        tag = AllowedTagFactory(name="focus")
        index = Page.objects.get(pk=tag_index.pk)
        page = StandardPage(title="Tagged", slug="tagged")
        index.add_child(instance=page)
        page.save_revision().publish()
        page.tags.add(tag)

        detail = TagDetailPage.objects.get(source_object_id=tag.pk)
        context = detail.get_context(_request())

        titles = {p.title for p in context["tagged_pages"]}
        assert "Tagged" in titles


def _request():
    return RequestFactory().get("/")
