"""Merged, visibility-scoped site search used by the search block."""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Q

from neuromancers_network.core.models.pages import MeetingDetailPage
from neuromancers_network.core.models.pages import PeerProfileDetailPage
from neuromancers_network.core.models.pages import StandardPage
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.selectors import published_meetings
from neuromancers_network.peers.models import PeerProfile
from neuromancers_network.peers.selectors import approved_peers

SEARCH_RESULTS_PER_KIND = 40
SEARCH_RESULTS_PER_PAGE = 20
MAX_QUERY_LENGTH = 200
SUMMARY_LENGTH = 200


@dataclass(frozen=True)
class SearchResult:
    kind: str
    title: str
    url: str
    summary: str


def _url_map(page_model, source_model, ids):
    if not ids:
        return {}
    pages = page_model.objects.filter(
        source_content_type=ContentType.objects.get_for_model(source_model),
        source_object_id__in=ids,
        live=True,
    )
    return {page.source_object_id: url for page in pages if (url := page.get_url())}


def _meeting_results(query, request):
    meetings = list(
        published_meetings(request=request)
        .filter(Q(title__icontains=query) | Q(description__icontains=query))
        .order_by("title", "pk")[:SEARCH_RESULTS_PER_KIND],
    )
    urls = _url_map(MeetingDetailPage, Meeting, [m.pk for m in meetings])
    return [
        SearchResult(
            kind="meeting",
            title=meeting.title,
            url=urls.get(meeting.pk) or meeting.get_absolute_url(),
            summary=(meeting.description or "")[:SUMMARY_LENGTH],
        )
        for meeting in meetings
    ]


def _peer_results(query, request):
    peers = list(
        approved_peers(request=request)
        .filter(
            Q(bio__icontains=query)
            | Q(user__name__icontains=query)
            | Q(user__username__icontains=query),
        )
        .order_by("user__name", "pk")[:SEARCH_RESULTS_PER_KIND],
    )
    urls = _url_map(PeerProfileDetailPage, PeerProfile, [p.pk for p in peers])
    return [
        SearchResult(
            kind="peer",
            title=peer.display_title,
            url=urls.get(peer.pk) or peer.get_absolute_url(),
            summary=(peer.bio or "")[:SUMMARY_LENGTH],
        )
        for peer in peers
    ]


def _page_results(query):
    pages = list(StandardPage.objects.live().public().search(query))
    pages.sort(key=lambda page: (page.title.casefold(), page.pk))
    return [
        SearchResult(
            kind="page",
            title=page.title,
            url=page.get_url() or "",
            summary=(page.search_description or "")[:SUMMARY_LENGTH],
        )
        for page in pages[:SEARCH_RESULTS_PER_KIND]
    ]


def search_site(query, *, request=None, page_number=1):
    """Return paginated, deterministic results across all searchable content."""
    query = (query or "").strip()[:MAX_QUERY_LENGTH]
    if not query:
        return {"query": "", "page_obj": None, "results": []}

    results = [
        *_meeting_results(query, request),
        *_peer_results(query, request),
        *_page_results(query),
    ]
    page_obj = Paginator(results, SEARCH_RESULTS_PER_PAGE).get_page(page_number)
    return {"query": query, "page_obj": page_obj, "results": page_obj.object_list}
