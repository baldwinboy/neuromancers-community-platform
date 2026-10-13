"""Seed the signed-in pages, home chrome, feeds and the contact form.

Idempotent: existing pages, menus and feeds are left untouched unless
``--force`` is passed, so admin edits are never clobbered by a re-run. Pages and
menus are seeded here rather than from a fixture because orderables, revisions
and page choosers do not survive flat fixtures.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from wagtail_daisIE.feeds.models import Feed
from wagtail_daisIE.menus.models import DaisyUIMenu

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import StandardPage
from neuromancers_network.moderation.models import SupportFormPage

#: Signed-in pages as ``(slug, title)``; gated to the ``authenticated`` audience.
SIGNED_IN_PAGES = [
    ("diary", "Diary"),
    ("inbox", "Inbox"),
    ("meetings", "Meetings"),
]

#: ``(name, context_model, header expression, text expression)`` for each feed.
FEEDS = [
    (
        "meetings-published",
        "meeting",
        "{{ meeting.title }}",
        "{{ meeting.description }}",
    ),
    (
        "bookings-upcoming",
        "booking",
        "{{ booking.status }}",
        "{{ booking.total_amount }}",
    ),
    (
        "unpaid-bookings",
        "unpaid_booking",
        "{{ unpaid_booking.status }}",
        "{{ unpaid_booking.total_amount }}",
    ),
    (
        "notifications-user",
        "notification",
        "{{ notification.title }}",
        "{{ notification.body }}",
    ),
    ("reviews-published", "review", "{{ review.rating }}", "{{ review.comment }}"),
    (
        "host_meeting",
        "host_meeting",
        "{{ host_meeting.title }}",
        "{{ host_meeting.status }}",
    ),
    (
        "host_request",
        "host_request",
        "{{ host_request.status }}",
        "{{ host_request.requested_start_time }}",
    ),
    (
        "host_refund",
        "host_refund",
        "{{ host_refund.reason }}",
        "{{ host_refund.status }}",
    ),
]


def _as_stream_data(value: Any) -> Any:
    """Recursively convert ``{"type", "value"}`` dicts to ``(type, value)`` tuples.

    Wagtail normalises the tuple form at every nesting level; the dict form
    leaves nested chooser instances (pages, snippets) unprepared and fails JSON
    serialisation on save.
    """
    if isinstance(value, dict):
        if "type" in value and "value" in value:
            return (value["type"], _as_stream_data(value["value"]))
        return {key: _as_stream_data(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_as_stream_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_as_stream_data(item) for item in value)
    return value


def _live_home() -> HomePage:
    home = HomePage.objects.live().first()
    if home is None:
        message = "No live HomePage found. Run migrations first."
        raise CommandError(message)
    return home


def _child(home: HomePage, slug: str):
    return home.get_children().filter(slug=slug).first()


def _ensure_signed_in_page(home: HomePage, slug: str, title: str, *, force: bool):
    existing = _child(home, slug)
    if existing is not None and not force:
        return existing.specific
    if existing is not None:
        existing.delete()
    page = StandardPage(title=title, slug=slug)
    home.add_child(instance=page)
    page.audience = _as_stream_data(
        [{"type": "audience", "value": {"audience": ["authenticated"]}}],
    )
    page.audience_denied = "403"
    page.save()
    page.save_revision().publish()
    return page


def _ensure_contact_page(home: HomePage, *, force: bool):
    existing = _child(home, "contact")
    if existing is not None and not force:
        return existing.specific
    if existing is not None:
        existing.delete()
    page = SupportFormPage(title="Contact", slug="contact")
    home.add_child(instance=page)
    page.save_revision().publish()
    return page


def _link_value(text: str, page) -> dict:
    return {
        "text": text,
        "destination": [{"type": "link_page", "value": page}],
        "open_in_new_tab": False,
    }


def _ensure_menus(home: HomePage, *, force: bool) -> None:
    pages = {slug: _child(home, slug) for slug in ("search", "dashboard", "settings")}
    nav_items = [{"type": "link", "value": _link_value("Home", home)}]
    nav_items += [
        {"type": "link", "value": _link_value(title, pages[slug])}
        for slug, title in (("search", "Search"), ("dashboard", "Dashboard"))
        if pages.get(slug) is not None
    ]
    _ensure_menu("Main navigation", layout="navbar", body=nav_items, force=force)

    footer_links = [_link_value("Home", home)]
    footer_links += [
        _link_value(title, pages[slug])
        for slug, title in (("search", "Search"), ("settings", "Settings"))
        if pages.get(slug) is not None
    ]
    footer_body = [
        {
            "type": "link_list",
            "value": {"heading": {"text": "Explore"}, "content": footer_links},
        },
    ]
    _ensure_menu("Footer", layout="footer", body=footer_body, force=force)


def _ensure_menu(name: str, *, layout: str, body: list, force: bool) -> DaisyUIMenu:
    menu, created = DaisyUIMenu.objects.get_or_create(
        name=name,
        defaults={"layout": layout},
    )
    if created or force:
        menu.layout = layout
        menu.body = _as_stream_data(body)
        menu.save()
    return menu


def _feed_card(header_expression: str, text_expression: str) -> list[dict]:
    return [
        {
            "type": "card",
            "value": {
                "content": [
                    {
                        "type": "header",
                        "value": {
                            "text": header_expression,
                            "design": {},
                            "audience": {},
                        },
                    },
                    {
                        "type": "text",
                        "value": {
                            "text": text_expression,
                            "design": {},
                            "audience": {},
                        },
                    },
                ],
                "design": {},
                "alignment": {},
                "audience": {},
            },
        },
    ]


def _ensure_feed(name: str, context_model: str, header: str, text: str, *, force: bool):
    feed, created = Feed.objects.get_or_create(
        name=name,
        defaults={
            "context_model": context_model,
            "order_by": "-created_at",
            "page_size": 6,
            "infinite": False,
            "empty_message": "Nothing to show yet.",
            "item": _feed_card(header, text),
        },
    )
    if created or force:
        feed.context_model = context_model
        feed.order_by = "-created_at"
        feed.item = _feed_card(header, text)
        feed.save()
    return feed


def _ensure_home_hero(home: HomePage, *, force: bool) -> None:
    if home.body and not force:
        return
    home.body = _as_stream_data(
        [
            {
                "type": "hero",
                "value": {
                    "overlay": True,
                    "full_width": True,
                    "align": "left",
                    "content": [
                        {
                            "type": "header",
                            "value": {
                                "text": "NEUROMANCERS Network",
                                "design": {},
                                "audience": {},
                            },
                        },
                        {
                            "type": "text",
                            "value": {
                                "text": "Find and offer online support.",
                                "design": {},
                                "audience": {},
                            },
                        },
                    ],
                    "design": {},
                    "alignment": {},
                    "audience": {},
                },
            },
        ],
    )
    home.save_revision().publish()


def seed_pages(*, force: bool = False) -> None:
    """Create the signed-in pages, home chrome, feeds and contact form."""
    home = _live_home()
    for slug, title in SIGNED_IN_PAGES:
        _ensure_signed_in_page(home, slug, title, force=force)
    _ensure_contact_page(home, force=force)
    _ensure_home_hero(home, force=force)
    _ensure_menus(home, force=force)
    for name, context_model, header, text in FEEDS:
        _ensure_feed(name, context_model, header, text, force=force)


class Command(BaseCommand):
    help = "Seed signed-in pages, home chrome, feeds and the contact form (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing content with the seed values.",
        )

    def handle(self, *args, **options):
        seed_pages(force=options["force"])
        self.stdout.write(
            self.style.SUCCESS("Pages, home chrome and feeds seeded."),
        )
