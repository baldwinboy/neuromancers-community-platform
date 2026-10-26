"""Seed the settings/self-service page body and account feeds.

Idempotent: an existing Settings page body is left untouched unless ``--force``
is passed. The page shell is a ``tabs`` block whose tab contents use the
``action_form`` (settings sections) and ``action`` (account controls) blocks.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from wagtail_daisIE.feeds.models import Feed

from neuromancers_network.core.models.pages import SettingsPage
from neuromancers_network.core.settings_audiences import ACTION_AUDIENCES
from neuromancers_network.core.settings_audiences import TAB_AUDIENCES

ACCOUNT_FEEDS = [
    ("blocked-users", "blocked_user"),
    ("payment-history", "payment_history"),
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


def _action(
    action: str,
    text: str,
    *,
    audience: list[str] | None = None,
) -> dict:
    return {
        "type": "action",
        "value": {
            "action": action,
            "target_expression": "",
            "button": _button(
                text,
                audience if audience is not None else ACTION_AUDIENCES.get(action),
            ),
            "confirmation": {},
        },
    }


def _action_form(
    action: str,
    text: str,
    *,
    audience: list[str] | None = None,
) -> dict:
    return {
        "type": "action_form",
        "value": {
            "action": action,
            "target_expression": "",
            "fields": [],
            "button": _button(
                text,
                audience if audience is not None else ACTION_AUDIENCES.get(action),
            ),
            "behaviour": "inline",
            "confirmation": {},
        },
    }


def _tab(
    label: str,
    key: str,
    content: list,
    *,
    audience: list[str] | None = None,
) -> dict:
    return {
        "label": label,
        "key": key,
        "icon": None,
        "audience": {
            "audience": (
                audience if audience is not None else TAB_AUDIENCES.get(key, [])
            ),
        },
        "content": content,
    }


def settings_page_body() -> list:
    """The Settings page body: a tabs block of self-service sections."""
    tabs = [
        _tab(
            "Account",
            "account",
            [
                _action_form("settings.account", "Save account"),
                _action_form("settings.profile", "Save profile"),
            ],
        ),
        _tab(
            "Privacy and safety",
            "privacy",
            [
                _action_form("settings.privacy", "Save privacy"),
                _action("account.delete_request", "Delete my account"),
            ],
        ),
        _tab(
            "Notifications",
            "notifications",
            [_action_form("settings.notifications", "Save notifications")],
        ),
        _tab(
            "Data and security",
            "security",
            [
                _action("data.export_request", "Request a data export"),
                _action("account.revoke_sessions", "Sign out everywhere"),
                _action("account.revoke_other_sessions", "Sign out other devices"),
                _action("calendar.rotate_token", "Rotate calendar feed"),
                _action("calendar.revoke_token", "Turn off calendar feed"),
            ],
        ),
        _tab(
            "Care provider",
            "provider",
            [
                _action("peer.accept_provider_agreement", "Accept provider agreement"),
                _action("peer.subscribe", "Start plan"),
                _action("peer.subscription_pause", "Pause plan"),
                _action("peer.subscription_resume", "Resume plan"),
                _action("peer.subscription_cancel", "Cancel plan"),
                _action("peer.connect_stripe", "Connect Stripe"),
                _action("peer.open_stripe_dashboard", "Open Stripe dashboard"),
                _action("peer.stripe_disconnect", "Disconnect Stripe"),
            ],
        ),
    ]
    return [
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


def _settings_page() -> SettingsPage:
    page = SettingsPage.objects.live().first() or SettingsPage.objects.first()
    if page is None:
        message = "No Settings page found. Run the chrome seed first."
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


def seed_account_selfservice(*, force: bool = False) -> None:
    page = _settings_page()
    if not page.body or force:
        page.body = _as_stream_data(settings_page_body())
        page.save_revision().publish()
    for name, context_model in ACCOUNT_FEEDS:
        _ensure_feed(name, context_model, force=force)


class Command(BaseCommand):
    help = "Seed the settings/self-service page body and account feeds (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite the existing page body with the seed values.",
        )

    def handle(self, *args, **options):
        seed_account_selfservice(force=options["force"])
        self.stdout.write(
            self.style.SUCCESS("Settings page body and account feeds seeded."),
        )
