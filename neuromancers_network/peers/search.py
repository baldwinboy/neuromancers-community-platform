from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from neuromancers_network.core.search import resolve_languages
from neuromancers_network.core.search import resolve_tag_slugs
from neuromancers_network.peers.models import PeerProfile

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.models import QuerySet

    from neuromancers_network.taxonomy.models import Language


def search_peers(
    *,
    languages: Sequence[Language | int | str] | None = None,
    tags: Sequence[str] | None = None,
    is_approved: bool | None = True,
    include_meeting_matches: bool = True,
    base_queryset: QuerySet[PeerProfile] | None = None,
) -> QuerySet[PeerProfile]:
    """
    Return peer profiles matching the given languages and tags.

    A peer matches a dimension when their own profile matches OR, when
    ``include_meeting_matches`` is set, when one of their offered meetings
    matches, so seekers can discover peers through meeting language/tag
    matches. When both languages and tags are supplied the peer must match
    within every supplied dimension (AND), while within a dimension any match
    counts (OR).
    """
    queryset = base_queryset if base_queryset is not None else PeerProfile.objects.all()
    if is_approved is not None:
        queryset = queryset.filter(is_approved=is_approved)
    if languages is not None:
        resolved = resolve_languages(languages)
        language_q = Q(languages__in=resolved)
        if include_meeting_matches:
            language_q |= Q(user__meetings__languages__in=resolved)
        queryset = queryset.filter(language_q)
    if tags is not None:
        slugs = resolve_tag_slugs(tags)
        tag_q = Q(tags__slug__in=slugs)
        if include_meeting_matches:
            tag_q |= Q(user__meetings__tags__slug__in=slugs)
        queryset = queryset.filter(tag_q)
    return queryset.distinct()
