from __future__ import annotations

import pytest
from django.test import RequestFactory
from wagtail.models import Page

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import StandardPage
from neuromancers_network.core.selectors import all_descendants
from neuromancers_network.core.selectors import immediate_children
from neuromancers_network.core.selectors import sitewide_pages
from neuromancers_network.taxonomy.tests.factories import AllowedTagFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def home() -> HomePage:
    page = HomePage.objects.first()
    if page is None:
        root = Page.get_first_root_node()
        page = HomePage(title="Home", slug="home")
        root.add_child(instance=page)
    return page


def _add(parent, title, slug, tags=(), *, live=True) -> StandardPage:
    page = StandardPage(title=title, slug=slug)
    if not live:
        page.live = False
    parent.add_child(instance=page)
    if live:
        page.save_revision().publish()
    for tag in tags:
        page.tags.add(tag)
    return page


def _request(**params):
    return RequestFactory().get("/", params)


class TestPageScopes:
    def test_immediate_children_only(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        child = _add(home, "Child", "child")
        grandchild = _add(child, "Grandchild", "grandchild")

        titles = {p.title for p in immediate_children(page=home)}
        assert titles == {"Child"}
        assert grandchild.title not in titles

    def test_all_descendants_includes_children_and_deeper(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        child = _add(home, "Child", "child")
        _add(child, "Grandchild", "grandchild")

        titles = {p.title for p in all_descendants(page=home)}
        assert titles == {"Child", "Grandchild"}

    def test_sitewide_pages_are_live_and_public(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        live = _add(home, "Live", "live")
        _add(home, "Draft", "draft", live=False)

        titles = {p.title for p in sitewide_pages()}
        assert live.title in titles
        assert "Draft" not in titles


class TestTagFiltering:
    def test_multi_tag_filter_is_deduped(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        tag_a = AllowedTagFactory(name="alpha")
        tag_b = AllowedTagFactory(name="beta")
        both = _add(home, "Both", "both", tags=(tag_a, tag_b))

        request = _request(tags=[tag_a.slug, tag_b.slug])
        results = list(sitewide_pages(request=request))

        assert [p.pk for p in results] == [both.pk]

    def test_host_page_fallback_from_query_string(self, home, settings):
        settings.WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES = ["core.StandardPage"]
        child = _add(home, "Child", "child")

        results = list(all_descendants(request=_request(page=home.pk)))
        assert [p.pk for p in results] == [child.pk]
