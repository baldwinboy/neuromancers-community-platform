from __future__ import annotations

from typing import TYPE_CHECKING

from neuromancers_network.core.search import resolve_languages
from neuromancers_network.core.search import resolve_tag_slugs
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.models import QuerySet

    from neuromancers_network.taxonomy.models import Language


def search_meetings(
    *,
    languages: Sequence[Language | int | str] | None = None,
    tags: Sequence[str] | None = None,
    status: str | None = MeetingStatus.PUBLISHED,
    base_queryset: QuerySet[Meeting] | None = None,
) -> QuerySet[Meeting]:
    """
    Return published meetings matching the given languages and tags.

    Languages and tags act as facets: when both are supplied a meeting must
    match within every supplied dimension (AND), while within a dimension any
    match counts (OR). Language entries may be ``Language`` objects, primary
    keys, or ISO 639-1 codes; tag entries are matched on their slug form so
    searches are case-insensitive.
    """
    queryset = base_queryset if base_queryset is not None else Meeting.objects.all()
    if status is not None:
        queryset = queryset.filter(status=status)
    if languages is not None:
        queryset = queryset.filter(languages__in=resolve_languages(languages))
    if tags is not None:
        queryset = queryset.filter(tags__slug__in=resolve_tag_slugs(tags))
    return queryset.distinct()
