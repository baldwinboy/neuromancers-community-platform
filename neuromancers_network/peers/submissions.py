"""Human-readable helpers for peer application form submissions."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext_lazy as _


def display_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(_("Yes") if value else _("No"))
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{humanize_key(key)}: {item}" for key, item in value.items())
    if value in (None, ""):
        return "—"
    return str(value)


def humanize_key(key: str) -> str:
    return str(key).replace("_", " ").replace("-", " ").strip().title()


def _submission_data(application) -> dict:
    submission = application.submission_record
    data = (submission.form_data if submission is not None else None) or (
        application.submission or {}
    )
    return data if isinstance(data, dict) else {}


def answer_rows(application) -> list[dict[str, str]]:
    """Return labelled answers, preferring the form page's current labels."""
    data = _submission_data(application)
    if not data:
        return []

    submission = application.submission_record
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    if submission is not None:
        page = submission.page.specific
        get_fields = getattr(page, "get_form_fields", None)
        if callable(get_fields):
            for field in get_fields():
                name = field.clean_name
                if name not in data:
                    continue
                rows.append(
                    {
                        "label": str(field.label or humanize_key(name)),
                        "value": display_value(data[name]),
                    },
                )
                seen.add(name)

    for name, value in data.items():
        if name not in seen:
            rows.append(
                {
                    "label": humanize_key(name),
                    "value": display_value(value),
                },
            )
    return rows


def summary(application, *, limit: int = 2, max_length: int = 100) -> str:
    """Return a short, label-free answer preview for admin list views."""
    data = _submission_data(application)
    if not data:
        return "—"
    parts = [
        f"{humanize_key(name)}: {display_value(value)}"
        for name, value in data.items()
        if value not in (None, "")
    ]
    return (" · ".join(parts[:limit]) or "—")[:max_length]
