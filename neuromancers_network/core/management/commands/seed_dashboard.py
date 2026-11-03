"""Seed the Dashboard tabs, account actions and account feeds."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from wagtail_daisIE.feeds.models import Feed

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models.pages import DashboardPage

ACCOUNT_FEEDS = [
    ("blocked-users", "blocked_user"),
    ("my-bookings", "my_bookings"),
    ("host-bookings", "host_bookings"),
    ("my-refunds", "my_refunds"),
    ("bookmarked-peers", "bookmarked_peer"),
    ("bookmarked-meetings", "bookmarked_meeting"),
]


def _as_stream_data(value: Any) -> Any:
    if isinstance(value, dict):
        if "type" in value and "value" in value:
            return (value["type"], _as_stream_data(value["value"]))
        return {key: _as_stream_data(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_as_stream_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_as_stream_data(item) for item in value)
    return value


def _button(text: str, audience: list[str] | None = None) -> dict:
    return {
        "text": text,
        "icon": "",
        "icon_after": True,
        "make_parent_clickable": False,
        "design": {},
        "audience": {"audience": audience or []},
    }


def _action(action: str, text: str, *, audience: list[str] | None = None) -> dict:
    return {
        "type": "action",
        "value": {
            "action": action,
            "target_expression": "",
            "button": _button(text, audience),
            "confirmation": {},
        },
    }


def _action_form(action: str, text: str) -> dict:
    return {
        "type": "action_form",
        "value": {
            "action": action,
            "target_expression": "",
            "fields": [],
            "button": _button(text),
            "behaviour": "inline",
            "confirmation": {},
        },
    }


def _page_button(text: str, page, *, audience: list[str] | None = None) -> dict:
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
            "audience": {"audience": audience or []},
        },
    }


def _url_button(text: str, url: str) -> dict:
    return {
        "type": "button",
        "value": {
            "text": text,
            "destination": [{"type": "link_url", "value": url}],
            "open_in_new_tab": False,
            "icon": "",
            "icon_after": True,
            "make_parent_clickable": False,
            "design": {},
            "audience": {},
        },
    }


def _text(text: str) -> dict:
    return {"type": "text", "value": {"text": text, "design": {}, "audience": {}}}


def _header(text: str) -> dict:
    return {"type": "header", "value": {"text": text, "design": {}, "audience": {}}}


def _tab(label: str, key: str, content: list, *, audience=None) -> dict:
    return {
        "label": label,
        "key": key,
        "icon": None,
        "audience": {"audience": audience or []},
        "content": [item for item in content if item is not None],
    }


def _home_pages(home: HomePage) -> dict:
    return {page.slug: page.specific for page in home.get_children().specific()}


def dashboard_page_body(home: HomePage) -> list:
    pages = _home_pages(home)
    shortcuts = [
        _page_button(
            "Upgrade to Care Provider",
            pages.get("join-the-network"),
            audience=["is_not_peer"],
        ),
        _page_button("My Bookings", pages.get("my-bookings")),
        _page_button("My Reviews", pages.get("my-reviews")),
        _page_button("My Bookmarks", pages.get("my-bookmarks")),
        _page_button(
            "Provider Bookings",
            pages.get("provider-bookings"),
            audience=["has_peer_profile"],
        ),
        _page_button(
            "Manage Sessions",
            pages.get("manage-sessions"),
            audience=["has_peer_profile"],
        ),
        _page_button(
            "Provider Reviews",
            pages.get("provider-reviews"),
            audience=["has_peer_profile"],
        ),
    ]

    tabs = [
        _tab(
            "Profile",
            "profile",
            [
                _action_form("settings.profile", "Save profile"),
                _page_button("Edit profile", pages.get("edit-profile")),
            ],
        ),
        _tab(
            "Notifications",
            "notifications",
            [_action_form("settings.notifications", "Save notifications")],
        ),
        _tab(
            "Calendar",
            "calendar",
            [
                _text("{{ calendar_feed_url }}"),
                _action(
                    "calendar.rotate_token",
                    "Rotate calendar feed",
                    audience=["can_rotate_calendar_feed"],
                ),
                _action(
                    "calendar.revoke_token",
                    "Disconnect calendar feed",
                    audience=["can_revoke_calendar_feed"],
                ),
            ],
        ),
        _tab(
            "Account",
            "account",
            [
                _action_form("settings.account", "Save account"),
                _url_button("Manage email", "/accounts/email/"),
                _url_button("Change password", "/accounts/password/change/"),
                _action("account.logout", "Sign out"),
                _action("account.revoke_sessions", "Sign out everywhere"),
                _action("account.revoke_other_sessions", "Sign out other devices"),
                _action(
                    "account.deactivate",
                    "Deactivate account",
                    audience=["can_deactivate_account"],
                ),
                _action(
                    "account.delete_request",
                    "Delete my account",
                    audience=["can_delete_account"],
                ),
            ],
        ),
        _tab(
            "Data + Security",
            "security",
            [
                _action(
                    "data.export_request",
                    "Request a data export",
                    audience=["can_request_data_export"],
                ),
                _action_form("settings.privacy", "Save privacy"),
            ],
        ),
        _tab(
            "Network Terms",
            "terms",
            [
                _action("accept_tos", "Accept Terms and Conditions"),
                _action(
                    "peer.accept_provider_agreement",
                    "Accept provider agreement",
                    audience=["can_accept_provider_agreement"],
                ),
            ],
        ),
        _tab(
            "Plan + Billing",
            "billing",
            [
                _action(
                    "peer.open_customer_portal",
                    "Manage subscription",
                    audience=["peer"],
                ),
                _action(
                    "peer.open_stripe_dashboard",
                    "Manage finances",
                    audience=["can_open_stripe_dashboard"],
                ),
                _action(
                    "peer.subscribe",
                    "Start plan",
                    audience=["can_start_plan"],
                ),
                _action(
                    "peer.connect_stripe",
                    "Connect Stripe",
                    audience=["can_connect_stripe"],
                ),
                _action(
                    "peer.stripe_disconnect",
                    "Disconnect Stripe",
                    audience=["can_disconnect_stripe"],
                ),
            ],
        ),
    ]

    return [
        _header("Your Dashboard"),
        *[item for item in shortcuts if item is not None],
        {
            "type": "tabs",
            "value": {
                "tabs": tabs,
                "style": "tabs-box",
                "size": "",
                "placement": "",
                "panel_design": {},
            },
        },
    ]


def _dashboard_page() -> DashboardPage:
    page = DashboardPage.objects.live().first() or DashboardPage.objects.first()
    if page is None:
        message = "No Dashboard page found. Run seed_pages first."
        raise CommandError(message)
    return page.specific


def _ensure_feed(name: str, context_model: str, *, force: bool) -> Feed:
    feed, created = Feed.objects.get_or_create(
        name=name,
        defaults={
            "context_model": context_model,
            "order_by": "-created_at",
            "page_size": 9,
            "infinite": False,
            "empty_message": "Nothing to show yet.",
        },
    )
    if created or force:
        feed.context_model = context_model
        feed.save()
    return feed


def seed_dashboard(*, force: bool = False) -> None:
    page = _dashboard_page()
    home = HomePage.objects.live().first()
    if home is None:
        message = "No live HomePage found. Run seed_pages first."
        raise CommandError(message)
    if not page.body or force:
        page.body = _as_stream_data(dashboard_page_body(home))
        page.save_revision().publish()
    for name, context_model in ACCOUNT_FEEDS:
        _ensure_feed(name, context_model, force=force)


class Command(BaseCommand):
    help = "Seed the Dashboard body and account feeds (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite the existing Dashboard body with the seed values.",
        )

    def handle(self, *args, **options):
        seed_dashboard(force=options["force"])
        self.stdout.write(
            self.style.SUCCESS("Dashboard body and account feeds seeded."),
        )
