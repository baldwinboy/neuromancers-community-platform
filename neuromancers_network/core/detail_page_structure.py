"""Create and reconcile the project's generated detail-page tree."""

from __future__ import annotations

import logging

from wagtail.coreutils import find_available_slug

from neuromancers_network.core.models.pages import BookingDetailTemplate
from neuromancers_network.core.models.pages import BookingGeneratedPagesIndexPage
from neuromancers_network.core.models.pages import MeetingDetailTemplate
from neuromancers_network.core.models.pages import MeetingGeneratedPagesIndexPage
from neuromancers_network.core.models.pages import MeetingIndexPage
from neuromancers_network.core.models.pages import PeerDetailTemplate
from neuromancers_network.core.models.pages import PeerGeneratedPagesIndexPage
from neuromancers_network.core.models.pages import PeerIndexPage
from neuromancers_network.core.models.pages import ProfileGeneratedPagesIndexPage
from neuromancers_network.core.models.pages import ProfileIndexPage
from neuromancers_network.core.models.pages import RefundRequestDetailTemplate
from neuromancers_network.core.models.pages import RefundRequestGeneratedPagesIndexPage
from neuromancers_network.core.models.pages import ReviewDetailTemplate
from neuromancers_network.core.models.pages import ReviewGeneratedPagesIndexPage
from neuromancers_network.core.models.pages import ReviewIndexPage
from neuromancers_network.core.models.pages import TagDetailTemplate
from neuromancers_network.core.models.pages import TagGeneratedPagesIndexPage
from neuromancers_network.core.models.pages import TagIndexPage
from neuromancers_network.core.models.pages import UserProfileDetailTemplate

logger = logging.getLogger(__name__)


INDEX_PAGES = (
    (MeetingIndexPage, "sessions", "Sessions"),
    (PeerIndexPage, "care-providers", "Care Providers"),
    (ReviewIndexPage, "reviews", "Reviews"),
    (TagIndexPage, "tags", "Tags"),
    (ProfileIndexPage, "u", "Members"),
)

TEMPLATE_PAGES = (
    (MeetingDetailTemplate, "meeting", "Meeting detail"),
    (PeerDetailTemplate, "peer_profile", "Care provider detail"),
    (ReviewDetailTemplate, "review", "Review detail"),
    (UserProfileDetailTemplate, "user_profile", "Member profile detail"),
    (TagDetailTemplate, "tag", "Tag detail"),
    (BookingDetailTemplate, "booking", "Booking detail"),
    (RefundRequestDetailTemplate, "refund_request", "Refund detail"),
)

GENERATED_INDEX_PAGES = (
    (
        MeetingGeneratedPagesIndexPage,
        MeetingIndexPage,
        "generated-meetings",
        "Generated meetings",
    ),
    (
        PeerGeneratedPagesIndexPage,
        PeerIndexPage,
        "generated-peers",
        "Generated care providers",
    ),
    (
        ReviewGeneratedPagesIndexPage,
        ReviewIndexPage,
        "generated-reviews",
        "Generated reviews",
    ),
    (
        ProfileGeneratedPagesIndexPage,
        ProfileIndexPage,
        "generated-profiles",
        "Generated profiles",
    ),
    (
        TagGeneratedPagesIndexPage,
        TagIndexPage,
        "generated-tags",
        "Generated tags",
    ),
    (
        BookingGeneratedPagesIndexPage,
        None,
        "generated-bookings",
        "Generated bookings",
    ),
    (
        RefundRequestGeneratedPagesIndexPage,
        None,
        "generated-refunds",
        "Generated refunds",
    ),
)


def _publish(page):
    if not page.live:
        page.save_revision().publish()
    return page


def _ensure_index(home, page_class, slug, title):
    page = page_class.objects.child_of(home).first()
    if page is None:
        page = page_class(
            title=title,
            slug=find_available_slug(home, slug),
        )
        home.add_child(instance=page)
    else:
        changed = False
        if page.title != title:
            page.title = title
            changed = True
        if page.slug != slug:
            page.slug = slug
            changed = True
        if changed:
            page.save()
            page.save_revision().publish()
    return _publish(page)


def _ensure_template(home, page_class, detail_key, title, *, force=False):
    from neuromancers_network.core.detail_template_seed import TEMPLATE_BODIES  # noqa: PLC0415

    page = page_class.objects.child_of(home).filter(detail_key=detail_key).first()
    if page is None:
        page = page_class(title=title, detail_key=detail_key)
        home.add_child(instance=page)
    if (not page.body or force) and detail_key in TEMPLATE_BODIES:
        page.body = TEMPLATE_BODIES[detail_key]()
        page.save_revision().publish()
    return _publish(page)


def _ensure_generated_index(parent, page_class, slug, title):
    page = page_class.objects.child_of(parent).first()
    if page is None:
        page = page_class(
            title=title,
            slug=find_available_slug(parent, slug),
        )
        parent.add_child(instance=page)
    return _publish(page)


def ensure_detail_page_structure(home, *, force: bool = False) -> None:
    """Create the index, template and generated-index pages if missing."""
    indexes = {}
    for page_class, slug, title in INDEX_PAGES:
        indexes[page_class] = _ensure_index(home, page_class, slug, title)

    for page_class, detail_key, title in TEMPLATE_PAGES:
        _ensure_template(home, page_class, detail_key, title, force=force)

    for page_class, parent_class, slug, title in GENERATED_INDEX_PAGES:
        parent = home if parent_class is None else indexes[parent_class]
        _ensure_generated_index(parent, page_class, slug, title)


def reconcile_detail_pages() -> None:
    """Delete non-public pages and move generated pages under their index."""
    from wagtail_daisIE.detail_pages.registry import get_detail_pages  # noqa: PLC0415

    for config in get_detail_pages().values():
        generated_index = config.get_generated_index_page()
        for page in config.page_type.objects.all():
            source = page.source
            publish = bool(
                source
                and (
                    not config.publish_field
                    or getattr(source, config.publish_field, False)
                ),
            )
            if source is None or not publish:
                page.delete()
            elif page.get_parent().pk != generated_index.pk:
                page.move(generated_index, pos="last-child")


def sync_detail_page_structure(home, *, force: bool = False) -> None:
    """Ensure the tree and reconcile existing pages."""
    ensure_detail_page_structure(home, force=force)
    reconcile_detail_pages()


__all__ = [
    "GENERATED_INDEX_PAGES",
    "INDEX_PAGES",
    "TEMPLATE_PAGES",
    "ensure_detail_page_structure",
    "reconcile_detail_pages",
    "sync_detail_page_structure",
]
