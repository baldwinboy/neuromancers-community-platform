"""Choice and query callables for daisIE feed filters.

daisIE's ``choice`` filters match on the related object's primary key, while the
taxonomy exposes ISO codes and slugs to the admin. These callables bridge the
two: the ``choices`` return stable codes/slugs (with human labels), and the
``query`` callables delegate to the domain search helpers so codes are resolved
correctly and the faceted semantics (AND across dimensions, OR within one) are
preserved.

A filter config may declare these as dotted paths. The per-tag-group filters are
computed lazily so no database query runs at settings import or app startup.
"""

from __future__ import annotations

from decimal import Decimal
from decimal import InvalidOperation
from functools import partial

from django.core.exceptions import AppRegistryNotReady
from django.db import DatabaseError
from django.db.models import F
from django.db.models import Min
from django.db.models.functions import Coalesce

from .models import AllowedTag
from .models import Country
from .models import Language
from .models import TagGroup


def language_choices() -> list[tuple[str, str]]:
    """Return ``(code, name)`` for every active language."""
    return [
        (language.code, language.name)
        for language in Language.objects.filter(is_active=True)
    ]


def country_choices() -> list[tuple[str, str]]:
    """Return ``(code, name)`` for every selectable country."""
    return [(country.code, country.name) for country in Country.objects.all()]


def tag_choices(group_slug: str | None = None) -> list[tuple[str, str]]:
    """Return ``(slug, name)`` for active tags, optionally within a group."""
    tags = AllowedTag.objects.filter(is_active=True)
    if group_slug is not None:
        tags = tags.filter(group__slug=group_slug)
    return [(tag.slug, tag.name) for tag in tags]


def _values(params, key) -> list[str]:
    if params is None:
        return []
    return [value for value in params.getlist(f"filter_{key}") if value]


def meeting_language_query(queryset, params, key):
    values = _values(params, key)
    if not values:
        return queryset
    from neuromancers_network.meetings.search import search_meetings  # noqa: PLC0415

    return search_meetings(languages=values, base_queryset=queryset)


def meeting_country_query(queryset, params, key):
    values = _values(params, key)
    if not values:
        return queryset
    from neuromancers_network.meetings.search import search_meetings  # noqa: PLC0415

    return search_meetings(countries=values, base_queryset=queryset)


def meeting_tag_query(queryset, params, key):
    values = _values(params, key)
    if not values:
        return queryset
    from neuromancers_network.meetings.search import search_meetings  # noqa: PLC0415

    return search_meetings(tags=values, base_queryset=queryset)


def peer_language_query(queryset, params, key):
    values = _values(params, key)
    if not values:
        return queryset
    from neuromancers_network.peers.search import search_peers  # noqa: PLC0415

    return search_peers(languages=values, base_queryset=queryset)


def peer_country_query(queryset, params, key):
    values = _values(params, key)
    if not values:
        return queryset
    from neuromancers_network.peers.search import search_peers  # noqa: PLC0415

    return search_peers(countries=values, base_queryset=queryset)


def peer_tag_query(queryset, params, key):
    values = _values(params, key)
    if not values:
        return queryset
    from neuromancers_network.peers.search import search_peers  # noqa: PLC0415

    return search_peers(tags=values, base_queryset=queryset)


def _decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation, TypeError, ValueError:
        return None


def meeting_amount_query(queryset, params, key):
    """Filter meetings by their effective price (tier minimum or flat price)."""
    minimum = _decimal(params.get(f"filter_{key}_min")) if params else None
    maximum = _decimal(params.get(f"filter_{key}_max")) if params else None
    if minimum is None and maximum is None:
        return queryset
    queryset = queryset.annotate(
        _effective_price=Coalesce(
            Min("price_tiers__options__amount"),
            F("price"),
        ),
    )
    if minimum is not None:
        queryset = queryset.filter(_effective_price__gte=minimum)
    if maximum is not None:
        queryset = queryset.filter(_effective_price__lte=maximum)
    return queryset


def _tag_group_specs(kind: str):
    """Yield one choice filter per active tag group (lazy, per first use).

    The query is guarded so system checks and ``makemigrations`` (which may
    evaluate filter choices before the table exists) never fail.
    """
    query = meeting_tag_query if kind == "meeting" else peer_tag_query
    try:
        groups = list(TagGroup.objects.filter(is_active=True).order_by("sort_order"))
    except DatabaseError, AppRegistryNotReady:  # pragma: no cover - pre-migration
        return
    for group in groups:
        yield (
            f"tag_group_{group.slug}",
            {
                "type": "choice",
                "field": "tags",
                "multi": True,
                "autocomplete": True,
                "label": group.name,
                "choices": partial(tag_choices, group.slug),
                "query": query,
            },
        )


class TagGroupFilterDict(dict):
    """Appends one feed filter per active tag group.

    The dynamic entries are produced by :meth:`items` on first access, so the
    database is only touched when the admin or a feed actually reads filters.
    """

    def __init__(self, base, kind):
        super().__init__(base or {})
        self._kind = kind

    def items(self):
        yield from super().items()
        yield from _tag_group_specs(self._kind)


def install_tag_group_filters() -> None:
    """Attach dynamic per-tag-group filters to the feed-capable context models."""
    from wagtail_daisIE.dynamic.registry import get_context_models  # noqa: PLC0415

    models = get_context_models()
    for model_key, kind in (("meeting", "meeting"), ("peer_profile", "peer")):
        config = models.get(model_key)
        if config is None:
            continue
        if not isinstance(config.filters_config, TagGroupFilterDict):
            config.filters_config = TagGroupFilterDict(config.filters_config, kind)
        config._resolved_filters = None  # noqa: SLF001
