from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.text import slugify

from neuromancers_network.taxonomy.models import Language

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.models import QuerySet


def resolve_languages(languages: Sequence[Language | int | str]) -> QuerySet[Language]:
    """
    Resolve language inputs into a single Language queryset.

    Entries may be ``Language`` objects, primary keys, or ISO 639-1 codes.
    Unknown codes resolve to an empty queryset, so results are deterministic
    (nothing matches) rather than erroring.
    """
    ids: list[int] = []
    codes: list[str] = []
    for item in languages:
        if isinstance(item, Language):
            ids.append(item.pk)
        elif isinstance(item, str):
            codes.append(item)
        else:
            ids.append(item)

    queryset = Language.objects.none()
    if ids:
        queryset |= Language.objects.filter(pk__in=ids)
    if codes:
        queryset |= Language.objects.filter(code__in=codes)
    return queryset


def resolve_tag_slugs(tags: Sequence[str]) -> list[str]:
    """
    Normalise tag names to taggit's lowercased slug form for matching.

    Taggit stores each tag with a slugged copy of its name, so matching on the
    slug makes searches robust to case and punctuation differences.
    """
    slugs = []
    for tag in tags:
        slug = slugify(tag)
        if slug:
            slugs.append(slug)
    return slugs
