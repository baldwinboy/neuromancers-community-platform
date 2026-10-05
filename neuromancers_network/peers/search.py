from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from neuromancers_network.core.search import resolve_countries
from neuromancers_network.core.search import resolve_languages
from neuromancers_network.core.search import resolve_tag_slugs
from neuromancers_network.peers.models import PeerProfile

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.models import QuerySet

    from neuromancers_network.taxonomy.models import Country
    from neuromancers_network.taxonomy.models import Language


def search_peers(  # noqa: PLR0913
    *,
    languages: Sequence[Language | int | str] | None = None,
    tags: Sequence[str] | None = None,
    countries: Sequence[Country | int | str] | None = None,
    is_approved: bool | None = True,
    include_meeting_matches: bool = True,
    base_queryset: QuerySet[PeerProfile] | None = None,
) -> QuerySet[PeerProfile]:
    """
    Return peer profiles matching the given languages, tags and countries.

    A peer matches a dimension when their own profile matches OR, when
    ``include_meeting_matches`` is set, when one of their offered meetings
    matches, so seekers can discover peers through meeting language/tag/country
    matches. When more than one dimension is supplied the peer must match
    within every supplied dimension (AND), while within a dimension any match
    counts (OR). Retired (inactive) tags never match.
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
        tag_q = Q(tags__is_active=True, tags__slug__in=slugs)
        if include_meeting_matches:
            tag_q |= Q(
                user__meetings__tags__is_active=True,
                user__meetings__tags__slug__in=slugs,
            )
        queryset = queryset.filter(tag_q)
    if countries is not None:
        resolved_countries = resolve_countries(countries)
        country_q = Q(countries__in=resolved_countries)
        if include_meeting_matches:
            country_q |= Q(user__meetings__countries__in=resolved_countries)
        queryset = queryset.filter(country_q)
    return queryset.distinct()
