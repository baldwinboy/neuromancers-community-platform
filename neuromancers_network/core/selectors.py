"""Query helpers for the page-tree feeds and tag pages."""

from __future__ import annotations

from django.apps import apps
from django.conf import settings
from wagtail.models import Page

from neuromancers_network.core.models.pages import StandardPage
from neuromancers_network.core.models.pages import TagDetailPage


def _allowed_page_types():
    """Page models permitted in the generic page feeds (allowlist)."""
    paths = getattr(settings, "WAGTAIL_DAISIE_PAGE_FEEDS_CONTENT_TYPES", []) or []
    models = []
    for path in paths:
        model = apps.get_model(path)
        if model is not None:
            models.append(model)
    return tuple(models)


def _host_page(request=None, page=None):
    """Return the host page from the served page or a ``?page=`` fallback."""
    if page is not None:
        return page
    pk = (getattr(request, "GET", None) or {}).get("page") if request else None
    if pk:
        return Page.objects.filter(pk=pk).first()
    return None


def _scoped(request, page):
    """Return ``(host, queryset)`` for host-relative feeds."""
    host = _host_page(request, page)
    if host is None:
        return None, Page.objects.none()
    allowed = _allowed_page_types()
    queryset = Page.objects.live().public()
    if allowed:
        queryset = queryset.type(*allowed)
    return host, queryset


def _tag_slugs(request):
    if request is None:
        return []
    getlist = getattr(getattr(request, "GET", None), "getlist", None)
    if getlist is None:
        return []
    return [slug for slug in getlist("tags") if slug]


def _apply_tag_filter(queryset, request):
    """Filter by selected tags using a deduping ``pk__in`` subquery."""
    slugs = _tag_slugs(request)
    if not slugs:
        return queryset
    tagged = StandardPage.objects.filter(tags__slug__in=slugs).values("pk")
    return queryset.filter(pk__in=tagged)


def host_page_only(request=None, page=None):
    """The host page as a one-item queryset (used by the ``host_page`` model)."""
    host = _host_page(request, page)
    if host is None:
        return Page.objects.none()
    return Page.objects.filter(pk=host.pk)


def sitewide_pages(request=None, page=None):
    """Every eligible live, public content page across all sites."""
    allowed = _allowed_page_types()
    queryset = Page.objects.live().public()
    if allowed:
        queryset = queryset.type(*allowed)
    queryset = queryset.order_by("-first_published_at")
    return _apply_tag_filter(queryset, request)


def all_descendants(request=None, page=None):
    """Every eligible descendant of the host page (any depth)."""
    host, queryset = _scoped(request, page)
    if host is None:
        return Page.objects.none()
    queryset = queryset.descendant_of(host).order_by("-first_published_at")
    return _apply_tag_filter(queryset, request)


def immediate_children(request=None, page=None):
    """The host page's direct children."""
    host, queryset = _scoped(request, page)
    if host is None:
        return Page.objects.none()
    queryset = queryset.child_of(host).order_by("-first_published_at")
    return _apply_tag_filter(queryset, request)


def deeper_descendants(request=None, page=None):
    """Descendants of the host page excluding its immediate children."""
    host, queryset = _scoped(request, page)
    if host is None:
        return Page.objects.none()
    queryset = (
        queryset.descendant_of(host)
        .exclude(depth=host.depth + 1)
        .order_by("-first_published_at")
    )
    return _apply_tag_filter(queryset, request)


def tag_page_children(request=None, page=None):
    """Generated ``TagDetailPage`` children of the host ``TagIndexPage``."""
    host = _host_page(request, page)
    if host is None:
        return TagDetailPage.objects.none()
    return TagDetailPage.objects.live().public().child_of(host).order_by("title")


def pages_tagged_with(tag):
    """Live, public ``StandardPage``s carrying *tag* (deduped)."""
    if tag is None:
        return StandardPage.objects.none()
    return (
        StandardPage.objects.live()
        .public()
        .filter(tags=tag)
        .order_by("-first_published_at")
        .distinct()
    )


def page_tag_choices(request=None, page=None):
    """Active ``AllowedTag`` options for the feed tag UI."""
    from neuromancers_network.taxonomy.models import AllowedTag  # noqa: PLC0415

    tags = (
        AllowedTag.objects.filter(is_active=True)
        .select_related("group")
        .order_by("group__sort_order", "sort_order", "name")
    )
    options = []
    for tag in tags:
        label = f"{tag.group.name} · {tag.name}" if tag.group_id else tag.name
        options.append({"value": tag.slug, "label": label})
    return options
