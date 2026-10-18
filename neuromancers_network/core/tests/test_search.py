from __future__ import annotations

import pytest
from django.test import RequestFactory
from wagtail.models import Page

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import StandardPage
from neuromancers_network.core.models.pages import SearchPage
from neuromancers_network.core.search_service import search_site
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.moderation.models import UserBlock
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

SUCCESS = 200


def _home() -> HomePage:
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="Home", slug="home")
        root.add_child(instance=home)
    return home


def _page(title, slug, *, description=""):
    page = StandardPage(
        title=title,
        slug=slug,
        search_description=description,
    )
    _home().add_child(instance=page)
    page.save_revision().publish()
    return page


class TestMergedSearch:
    def test_merges_and_orders_results(self):
        _home()
        peer = make_peer()
        profile = peer.peer_profile
        profile.bio = "Needle provider"
        profile.save()
        create_meeting(peer=peer, title="Needle meeting")
        _page("Needle page", "needle-page")

        result = search_site("needle")

        kinds = [item.kind for item in result["results"]]
        assert kinds == ["meeting", "peer", "page"]
        assert all(item.url for item in result["results"])

    def test_finds_pages_by_search_description(self):
        _page("Unrelated", "unrelated", description="needle description")

        result = search_site("needle")

        assert [item.kind for item in result["results"]] == ["page"]

    def test_empty_query_returns_nothing(self):
        assert search_site("")["results"] == []

    def test_results_are_paginated(self, monkeypatch):
        results_per_page = 2
        monkeypatch.setattr(
            "neuromancers_network.core.search_service.SEARCH_RESULTS_PER_PAGE",
            results_per_page,
        )
        for index in range(3):
            _page(f"needle {index}", f"needle-{index}")

        result = search_site("needle")

        assert len(result["results"]) == results_per_page
        assert result["page_obj"].paginator.num_pages == results_per_page

    def test_blocked_peer_results_are_hidden(self):
        peer = make_peer()
        create_meeting(peer=peer, title="Needle meeting")
        viewer = UserFactory()
        UserBlock.objects.create(blocker=viewer, blocked=peer)
        request = RequestFactory().get("/")
        request.user = viewer

        result = search_site("needle", request=request)

        assert not [
            item for item in result["results"] if item.kind in {"meeting", "peer"}
        ]


class TestSearchPage:
    def test_renders_merged_results(self, client):
        home = _home()
        create_meeting(peer=make_peer(), title="Needle meeting")
        page = SearchPage(title="Search", slug="search-test")
        home.add_child(instance=page)
        page.save_revision().publish()

        response = client.get(page.get_url(), {"query": "needle"})

        assert response.status_code == SUCCESS
        content = response.content.decode()
        assert "Needle meeting" in content
        assert "No results" not in content
