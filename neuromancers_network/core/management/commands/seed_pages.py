"""Seed the page tree, Dashboard chrome, feeds and detail templates.

Idempotent: existing page content is left untouched unless ``--force`` is
passed, so admin edits are never clobbered by a re-run. Structural chrome
(Settings retirement, index slugs, navigation) is always reconciled.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from wagtail_daisIE.detail_pages.validation import validate_detail_pages
from wagtail_daisIE.feeds.models import Feed
from wagtail_daisIE.menus.models import DaisyUIMenu

from neuromancers_network.core.detail_page_structure import sync_detail_page_structure
from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import StandardPage
from neuromancers_network.core.models.pages import DashboardPage
from neuromancers_network.core.models.pages import SettingsPage
from neuromancers_network.meetings.forms_pages import BookingFormPage
from neuromancers_network.meetings.forms_pages import MeetingEditFormPage
from neuromancers_network.meetings.forms_pages import MeetingFormPage
from neuromancers_network.meetings.forms_pages import RefundRequestFormPage
from neuromancers_network.meetings.forms_pages import ReviewFormPage
from neuromancers_network.moderation.models import SupportFormPage
from neuromancers_network.peers.forms_pages import PeerApplicationEditFormPage
from neuromancers_network.peers.forms_pages import PeerApplicationFormPage
from neuromancers_network.users.forms_pages import ProfileEditFormPage

#: Account/content pages as ``(slug, title)``.
CONTENT_PAGES = [
    ("my-bookings", "My Bookings"),
    ("my-reviews", "My Reviews"),
    ("my-bookmarks", "My Bookmarks"),
]

PROVIDER_PAGES = [
    ("provider-bookings", "Provider Bookings"),
    ("manage-sessions", "Manage Sessions"),
    ("provider-reviews", "Provider Reviews"),
]

FORM_PAGES = [
    (PeerApplicationFormPage, "join-the-network", "Join the Network"),
    (PeerApplicationEditFormPage, "edit-application", "Edit Application"),
    (MeetingFormPage, "create-session", "Create Session"),
    (MeetingEditFormPage, "edit-session", "Edit Session"),
    (BookingFormPage, "booking", "Book a Session"),
    (RefundRequestFormPage, "request-refund", "Request Refund"),
    (ReviewFormPage, "write-review", "Write a Review"),
    (ProfileEditFormPage, "edit-profile", "Edit Profile"),
]

#: ``(name, context_model, header, text, url)`` for each feed.
FEEDS = [
    (
        "sessions",
        "meeting",
        "{{ meeting.title }}",
        "{{ meeting.description }}",
        "{{ meeting.url }}",
    ),
    (
        "care-providers",
        "peer_profile",
        "{{ peer_profile.display_title }}",
        "{{ peer_profile.bio }}",
        "{{ peer_profile.url }}",
    ),
    (
        "my-bookings",
        "my_bookings",
        "{{ my_bookings.meeting.title }}",
        (
            "{{ my_bookings.status }} — "
            "{{ my_bookings.total_amount }} {{ my_bookings.currency }}"
        ),
        "{{ my_bookings.url }}",
    ),
    (
        "host-bookings",
        "host_bookings",
        "{{ host_bookings.meeting.title }}",
        (
            "{{ host_bookings.status }} — "
            "{{ host_bookings.total_amount }} {{ host_bookings.currency }}"
        ),
        "{{ host_bookings.url }}",
    ),
    (
        "my-refunds",
        "my_refunds",
        "{{ my_refunds.reason }}",
        "{{ my_refunds.status }}",
        "{{ my_refunds.url }}",
    ),
    (
        "my-reviews",
        "my_authored_reviews",
        "{{ my_authored_reviews.rating }}",
        "{{ my_authored_reviews.comment }}",
        "{{ my_authored_reviews.url }}",
    ),
    (
        "provider-reviews",
        "my_reviews",
        "{{ my_reviews.rating }}",
        "{{ my_reviews.comment }}",
        "{{ my_reviews.url }}",
    ),
    (
        "bookmarked-peers",
        "bookmarked_peer",
        "{{ bookmarked_peer.display_title }}",
        "{{ bookmarked_peer.bio }}",
        "{{ bookmarked_peer.url }}",
    ),
    (
        "bookmarked-meetings",
        "bookmarked_meeting",
        "{{ bookmarked_meeting.title }}",
        "{{ bookmarked_meeting.description }}",
        "{{ bookmarked_meeting.url }}",
    ),
    (
        "notifications",
        "notification",
        "{{ notification.title }}",
        "{{ notification.body }}",
        "",
    ),
    (
        "host-meetings",
        "host_meeting",
        "{{ host_meeting.title }}",
        "{{ host_meeting.status }}",
        "{{ host_meeting.url }}",
    ),
    (
        "host-requests",
        "host_request",
        "{{ host_request.status }}",
        "{{ host_request.requested_start_time }}",
        "",
    ),
    (
        "host-refunds",
        "host_refund",
        "{{ host_refund.reason }}",
        "{{ host_refund.status }}",
        "",
    ),
]


def _as_stream_data(value: Any) -> Any:
    """Recursively convert ``{"type", "value"}`` dicts to ``(type, value)`` tuples."""
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


def _audience(value: list[str] | None = None) -> dict:
    return {"audience": value or []}


def _publish(page):
    if not page.live:
        page.save_revision().publish()
    return page


def _ensure_content_page(
    home: HomePage,
    slug: str,
    title: str,
    *,
    audience: list[str] | None = None,
    force: bool = False,
):
    existing = _child(home, slug)
    if existing is not None and not force:
        return existing.specific
    if existing is not None:
        existing.delete()
    page = StandardPage(title=title, slug=slug)
    home.add_child(instance=page)
    page.audience = _as_stream_data(
        [{"type": "audience", "value": _audience(audience)}],
    )
    page.audience_denied = "403" if audience else ""
    page.save()
    return _publish(page)


def _ensure_dashboard(home: HomePage) -> DashboardPage:
    page = DashboardPage.objects.child_of(home).first()
    if page is None:
        page = DashboardPage(title="Dashboard", slug="dashboard")
        home.add_child(instance=page)
    return _publish(page)


def _ensure_form_page(
    home: HomePage,
    page_class,
    slug: str,
    title: str,
    *,
    force=False,
):
    existing = page_class.objects.child_of(home).first()
    if existing is not None and not force:
        return existing.specific
    if existing is not None:
        existing.delete()
    page = page_class(title=title, slug=slug)
    home.add_child(instance=page)
    return _publish(page)


def _ensure_contact_page(home: HomePage, *, force: bool):
    existing = _child(home, "contact")
    if existing is not None and not force:
        return existing.specific
    if existing is not None:
        existing.delete()
    page = SupportFormPage(title="Contact", slug="contact")
    home.add_child(instance=page)
    return _publish(page)


def _link_value(text: str, page) -> dict:
    return {
        "text": text,
        "destination": [{"type": "link_page", "value": page}],
        "open_in_new_tab": False,
        "audience": _audience(),
    }


def _url_link(text: str, url: str, *, audience: list[str] | None = None) -> dict:
    return {
        "text": text,
        "destination": [{"type": "link_url", "value": url}],
        "open_in_new_tab": False,
        "audience": _audience(audience),
    }


def _action_value(
    action: str,
    text: str,
    *,
    audience: list[str] | None = None,
    icon: str = "",
) -> dict:
    return {
        "type": "action",
        "value": {
            "action": action,
            "target_expression": "",
            "button": {
                "text": text,
                "icon": icon,
                "icon_after": True,
                "make_parent_clickable": False,
                "design": {},
                "audience": _audience(audience),
            },
            "confirmation": {},
        },
    }


def _ensure_menus(home: HomePage, *, force: bool) -> None:
    pages = {
        slug: _child(home, slug)
        for slug in (
            "sessions",
            "care-providers",
            "join-the-network",
            "my-bookings",
            "dashboard",
            "contact",
        )
    }

    nav_items = []
    if pages.get("sessions") is not None:
        nav_items.append(
            {
                "type": "link",
                "value": _link_value("Explore the Network", pages["sessions"]),
            },
        )
    if pages.get("join-the-network") is not None:
        nav_items.append(
            {
                "type": "link",
                "value": _link_value(
                    "Become A Care Provider",
                    pages["join-the-network"],
                ),
            },
        )
    if pages.get("dashboard") is not None:
        nav_items.append(
            {"type": "link", "value": _link_value("Your Account", pages["dashboard"])},
        )
    nav_items.append(
        {
            "type": "link_list",
            "value": {
                "heading": {"text": "Help", "design": {}, "audience": {}},
                "content": [
                    _url_link(
                        "Help Centre",
                        "https://neuromancers.org.uk/about#contact",
                    ),
                    _url_link(
                        "Contact Us",
                        "https://neuromancers.org.uk/about#contact",
                    ),
                ],
                "design": {},
                "audience": {},
            },
        },
    )
    nav_items.append(
        {
            "type": "link",
            "value": {
                **_url_link("Sign up", "/signup/", audience=["not_logged_in"]),
                "icon": "user",
            },
        },
    )
    nav_items.append(
        _action_value(
            "account.logout",
            "Sign out",
            audience=["authenticated"],
            icon="arrow-right-start-on-rectangle",
        ),
    )

    footer_links = [_link_value("Home", home)]
    if pages.get("my-bookings") is not None:
        footer_links.append(_link_value("My Bookings", pages["my-bookings"]))
    if pages.get("dashboard") is not None:
        footer_links.append(_link_value("Your Account", pages["dashboard"]))
    footer_body = [
        {
            "type": "link_list",
            "value": {
                "heading": {"text": "Explore", "design": {}, "audience": {}},
                "content": footer_links,
                "design": {},
                "audience": {},
            },
        },
        {
            "type": "link_list",
            "value": {
                "heading": {"text": "Help", "design": {}, "audience": {}},
                "content": [
                    _url_link(
                        "Help Centre",
                        "https://neuromancers.org.uk/about#contact",
                    ),
                    _url_link(
                        "Contact Us",
                        "https://neuromancers.org.uk/about#contact",
                    ),
                ],
                "design": {},
                "audience": {},
            },
        },
    ]

    branding = [
        {
            "type": "branding",
            "value": {
                "logo": {},
                "logo_after": False,
                "wordmark": {
                    "text": "NEUROMANCERS Network",
                    "design": {},
                    "audience": {},
                },
                "destination": [{"type": "link_page", "value": home}],
                "open_in_new_tab": False,
                "design": {},
                "audience": {},
            },
        },
    ]
    _ensure_menu(
        "Navigation",
        layout="navbar",
        body=nav_items,
        branding=branding,
        force=force,
    )
    _ensure_menu("Footer", layout="footer", body=footer_body, force=force)


def _ensure_menu(
    name: str,
    *,
    layout: str,
    body: list,
    branding: list | None = None,
    force: bool,
) -> DaisyUIMenu:
    names = [name]
    if name == "Navigation":
        names.append("Main navigation")
    menu = DaisyUIMenu.objects.filter(name__in=names).order_by("pk").first()
    if menu is None:
        menu = DaisyUIMenu(name=name, layout=layout)
    menu.name = name
    menu.layout = layout
    menu.body = _as_stream_data(body)
    if branding is not None:
        menu.branding = _as_stream_data(branding)
    menu.save()
    return menu


def _feed_action(action: str, text: str, target: str) -> dict:
    return {
        "type": "action",
        "value": {
            "action": action,
            "target_expression": target,
            "button": {
                "text": text,
                "icon": "",
                "icon_after": True,
                "make_parent_clickable": False,
                "design": {},
                "audience": {},
            },
            "confirmation": {},
        },
    }


def _feed_card(  # noqa: PLR0913
    header: str,
    text: str,
    url: str,
    *,
    actions: list[tuple[str, str]] | None = None,
    target: str = "",
    receipt: bool = False,
) -> list[dict]:
    content = [
        {"type": "header", "value": {"text": header, "design": {}, "audience": {}}},
        {"type": "text", "value": {"text": text, "design": {}, "audience": {}}},
    ]
    if url:
        content.append(
            {
                "type": "button",
                "value": {
                    "text": "View",
                    "destination": [{"type": "link_url", "value": url}],
                    "open_in_new_tab": False,
                    "icon": "",
                    "icon_after": True,
                    "make_parent_clickable": False,
                    "design": {},
                    "audience": {},
                },
            },
        )
    if receipt:
        content.append(
            {
                "type": "button",
                "value": {
                    "text": "Receipt",
                    "destination": [
                        {"type": "link_url", "value": "{{ my_bookings.receipt_url }}"},
                    ],
                    "open_in_new_tab": True,
                    "icon": "",
                    "icon_after": True,
                    "make_parent_clickable": False,
                    "design": {},
                    "audience": {},
                },
            },
        )
    for action, label in actions or []:
        content.append(_feed_action(action, label, target))
    return [
        {
            "type": "card",
            "value": {
                "content": content,
                "design": {},
                "alignment": {},
                "audience": {},
            },
        },
    ]


def _ensure_feed(  # noqa: PLR0913
    name: str,
    context_model: str,
    header: str,
    text: str,
    url: str,
    *,
    force: bool,
):
    item_kwargs = {}
    if name == "host-requests":
        item_kwargs = {
            "actions": [
                ("bookings.approve", "Approve"),
                ("bookings.reject", "Reject"),
            ],
            "target": "{{ host_request.pk }}",
        }
    elif name == "host-meetings":
        item_kwargs = {
            "actions": [
                ("meetings.publish", "Publish"),
                ("meetings.unpublish", "Unpublish"),
                ("meetings.archive", "Archive"),
                ("meetings.delete", "Delete"),
            ],
            "target": "{{ host_meeting.pk }}",
        }
    elif name == "provider-reviews":
        item_kwargs = {
            "actions": [
                ("review.approve", "Approve"),
                ("review.hide", "Hide"),
            ],
            "target": "{{ my_reviews.pk }}",
        }
    elif name == "my-bookings":
        item_kwargs = {"receipt": True}

    feed, created = Feed.objects.get_or_create(
        name=name,
        defaults={
            "context_model": context_model,
            "order_by": "-created_at",
            "page_size": 6,
            "infinite": False,
            "empty_message": "Nothing to show yet.",
            "item": _feed_card(header, text, url, **item_kwargs),
        },
    )
    if created or force:
        feed.context_model = context_model
        feed.order_by = "-created_at"
        feed.item = _feed_card(header, text, url, **item_kwargs)
        feed.save()
    return feed


def _feed_block(name: str) -> dict | None:
    feed = Feed.objects.filter(name=name).first()
    if feed is None:
        return None
    return {"type": "feed", "value": {"feed": feed, "layout": {}}}


def _tabs_block(tabs: list[dict]) -> dict:
    return {
        "type": "tabs",
        "value": {
            "tabs": tabs,
            "style": "tabs-box",
            "size": "",
            "placement": "",
            "panel_design": {},
        },
    }


def _tab(label: str, key: str, content: list, *, audience=None) -> dict:
    return {
        "label": label,
        "key": key,
        "icon": None,
        "audience": _audience(audience),
        "content": [item for item in content if item is not None],
    }


def _header_block(text: str) -> dict:
    return {"type": "header", "value": {"text": text, "design": {}, "audience": {}}}


def _text_block(text: str) -> dict:
    return {"type": "text", "value": {"text": text, "design": {}, "audience": {}}}


def _page_button(text: str, page) -> dict | None:
    if page is None:
        return None
    return {
        "type": "button",
        "value": {
            "text": text,
            "destination": [{"type": "link_page", "value": page}],
            "open_in_new_tab": False,
            "icon": "",
            "icon_after": True,
            "make_parent_clickable": False,
            "design": {},
            "audience": {},
        },
    }


def _page_body(slug: str) -> list[dict]:  # noqa: PLR0911
    if slug == "sessions":
        return [
            _tabs_block(
                [
                    _tab("Sessions View", "sessions", [_feed_block("sessions")]),
                    _tab(
                        "Provider View",
                        "providers",
                        [_feed_block("care-providers")],
                    ),
                ],
            ),
        ]
    if slug == "my-bookings":
        return [
            _header_block("Upcoming and past bookings"),
            _feed_block("my-bookings"),
            _header_block("Refund requests"),
            _feed_block("my-refunds"),
        ]
    if slug == "my-reviews":
        return [_header_block("Reviews I wrote"), _feed_block("my-reviews")]
    if slug == "my-bookmarks":
        return [
            _header_block("Care providers"),
            _feed_block("bookmarked-peers"),
            _header_block("Meetings"),
            _feed_block("bookmarked-meetings"),
        ]
    if slug == "provider-bookings":
        return [
            _header_block("Bookings for your sessions"),
            _feed_block("host-bookings"),
            _header_block("Booking requests"),
            _feed_block("host-requests"),
        ]
    if slug == "manage-sessions":
        home = HomePage.objects.live().first()
        create_page = (
            home.get_children().filter(slug="create-session").first()
            if home is not None
            else None
        )
        return [
            _header_block("Your sessions"),
            _page_button("Create a session", create_page),
            _feed_block("host-meetings"),
        ]
    if slug == "provider-reviews":
        return [
            _header_block("Reviews received"),
            _feed_block("provider-reviews"),
        ]
    return []


def _ensure_page_body(home: HomePage, slug: str, *, force: bool) -> None:
    page = _child(home, slug)
    if page is None:
        return
    page = page.specific
    if page.body and not force:
        return
    body = _page_body(slug)
    if not body:
        return
    page.body = _as_stream_data(body)
    page.save_revision().publish()


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
                    "content": [
                        _header_block("NEUROMANCERS Network"),
                        _text_block("Find and offer online support."),
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
    """Create the page tree, navigation, feeds and shared detail templates."""
    home = _live_home()

    # Retire the old Settings experience.
    SettingsPage.objects.all().delete()

    for name, context_model, header, text, url in FEEDS:
        _ensure_feed(name, context_model, header, text, url, force=force)

    # Detail templates reference feeds by name, so sync them first.
    sync_detail_page_structure(home, force=force)
    _ensure_dashboard(home)

    for slug, title in CONTENT_PAGES:
        _ensure_content_page(
            home,
            slug,
            title,
            audience=["authenticated"],
            force=force,
        )
    for slug, title in PROVIDER_PAGES:
        _ensure_content_page(
            home,
            slug,
            title,
            audience=["has_peer_profile"],
            force=force,
        )
    for page_class, slug, title in FORM_PAGES:
        _ensure_form_page(home, page_class, slug, title, force=force)
    _ensure_contact_page(home, force=force)
    _ensure_home_hero(home, force=force)
    _ensure_menus(home, force=force)
    for slug, _title in CONTENT_PAGES + PROVIDER_PAGES:
        _ensure_page_body(home, slug, force=force)
    _ensure_page_body(home, "sessions", force=force)
    validate_detail_pages(records=True)


class Command(BaseCommand):
    help = "Seed pages, navigation, feeds and detail templates (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing content with the seed values.",
        )

    def handle(self, *args, **options):
        seed_pages(force=options["force"])
        self.stdout.write(
            self.style.SUCCESS("Pages, navigation, feeds and templates seeded."),
        )
