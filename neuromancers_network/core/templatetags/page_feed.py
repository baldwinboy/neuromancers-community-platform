"""Template tags for the page-tree feed template override."""

from __future__ import annotations

from django import template

from neuromancers_network.core.selectors import page_tag_choices

register = template.Library()

PAGE_FEED_MODELS = frozenset(
    {
        "page_sitewide",
        "page_all",
        "page_children",
        "page_deeper",
        "tag_page_children",
    },
)


@register.simple_tag
def is_page_feed(context_model):
    """True when *context_model* is one of the page-tree feed models."""
    return context_model in PAGE_FEED_MODELS


@register.simple_tag(takes_context=True)
def page_tag_options(context):
    """Active tag options for the feed tag UI."""
    request = context.get("request")
    page = context.get("host_page") or context.get("page")
    return page_tag_choices(request, page)


@register.simple_tag(takes_context=True)
def page_tag_selected(context):
    """Slugs currently selected in the tag filter."""
    request = context.get("request")
    getlist = getattr(getattr(request, "GET", None), "getlist", None)
    return getlist("tags") if getlist is not None else []
