"""Seed allauth and inbox notification email templates."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from django.conf import settings

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).with_name("email_seed.yaml")


def _load_data() -> dict:
    if not DATA_PATH.exists():
        return {}
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _button(text: str, url: str) -> dict:
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


def _email_body(spec: dict, *, default_url: str) -> list[tuple]:
    blocks = [
        ("header", {"text": spec.get("heading") or spec.get("subject", "")}),
        ("text", {"text": spec.get("text", "")}),
    ]
    if spec.get("button"):
        blocks.append(
            (
                "button",
                _button(
                    spec["button"],
                    spec.get("url") or default_url,
                )["value"],
            ),
        )
    return blocks


def _theme():
    from wagtail_daisIE.models import DaisyUITheme  # noqa: PLC0415

    return DaisyUITheme.objects.filter(name="neuromancers").first()


def _ensure_template(  # noqa: PLR0913
    *,
    name: str,
    template_key: str,
    subject: str,
    preheader: str,
    body: list[tuple],
    force: bool,
):
    from wagtail_daisIE.notifications.models import EmailTemplate  # noqa: PLC0415

    template = EmailTemplate.objects.filter(template_key=template_key).first()
    if template is None:
        template = EmailTemplate(name=name, template_key=template_key)
    if template.name != name:
        template.name = name
    template.template_key = template_key
    template.subject = subject
    template.preheader = preheader
    template.email_theme = _theme()
    if force or not template.content:
        template.content = body
    template.save()
    return template


def _curated_event(key: str, label: str) -> dict:
    data = _load_data().get("events", {})
    if key in data:
        return data[key]
    name = label or key.replace("_", " ").title()
    return {
        "name": name,
        "subject": name,
        "preheader": f"Update from NEUROMANCERS: {name}",
        "heading": name,
        "text": "Open your dashboard to see the latest details.",
        "button": "Open your dashboard",
    }


def seed_allauth_templates(*, force: bool = False) -> int:
    from wagtail_daisIE.allauth_emails.catalogue import get_allauth_emails  # noqa: PLC0415
    from wagtail_daisIE.allauth_emails.models import AllauthEmailOverride  # noqa: PLC0415

    curated = _load_data().get("allauth", {})
    count = 0
    for email in get_allauth_emails():
        spec = curated.get(email.prefix) or {
            "subject": str(email.label),
            "preheader": "A message from NEUROMANCERS",
            "heading": str(email.label),
            "text": "Open the link in this email to continue.",
        }
        template = _ensure_template(
            name=f"Authentication — {email.label}",
            template_key=f"allauth:{email.prefix}",
            subject=spec.get("subject") or str(email.label),
            preheader=spec.get("preheader") or "",
            body=_email_body(
                spec,
                default_url="{{ payload.activate_url }}",
            ),
            force=force,
        )
        AllauthEmailOverride.objects.update_or_create(
            template_prefix=email.prefix,
            defaults={"email_template": template, "is_active": True},
        )
        count += 1
    return count


def seed_event_templates(*, force: bool = False) -> int:
    from neuromancers_network.inbox.models import DaisieBridgeSubscriber  # noqa: PLC0415

    bridges = getattr(settings, "WAGTAIL_DAISIE_NOTIFICATION_BRIDGES", {})
    count = 0
    for key, config in bridges.items():
        label = str(config.get("label") or key.replace("_", " ").title())
        spec = _curated_event(key, label)

        template = None
        if key == "account_created":
            # Adopt the captured Welcome Email rather than creating a duplicate.
            from wagtail_daisIE.notifications.models import EmailTemplate  # noqa: PLC0415

            template = (
                EmailTemplate.objects.filter(name__iexact="Welcome Email").first()
                or EmailTemplate.objects.filter(template_key=key).first()
            )
        if template is None:
            template = _ensure_template(
                name=spec.get("name") or label,
                template_key=key,
                subject=spec.get("subject") or label,
                preheader=spec.get("preheader") or "",
                body=_email_body(
                    spec,
                    default_url="{{ payload.dashboard_url }}",
                ),
                force=force,
            )
        else:
            template.template_key = key
            template.subject = spec.get("subject") or label
            template.preheader = spec.get("preheader") or ""
            template.email_theme = _theme()
            if force or not template.content:
                template.content = _email_body(
                    spec,
                    default_url="{{ payload.dashboard_url }}",
                )
            template.save()

        DaisieBridgeSubscriber.objects.update_or_create(
            event_type=key,
            defaults={"label": label, "is_active": True},
        )
        count += 1
    return count


def seed_email_templates(*, force: bool = False) -> dict:
    return {
        "allauth": seed_allauth_templates(force=force),
        "events": seed_event_templates(force=force),
    }


__all__ = [
    "seed_allauth_templates",
    "seed_email_templates",
    "seed_event_templates",
]
