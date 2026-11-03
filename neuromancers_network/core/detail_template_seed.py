"""Seed bodies for the shared detail-template pages."""

from __future__ import annotations


def _as_stream_data(value):
    """Convert ``{"type", "value"}`` dicts into Wagtail's tuple form."""
    if isinstance(value, dict):
        if "type" in value and "value" in value:
            return (value["type"], _as_stream_data(value["value"]))
        return {key: _as_stream_data(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_as_stream_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_as_stream_data(item) for item in value)
    return value


def _text(text: str) -> dict:
    return {
        "type": "text",
        "value": {"text": text, "design": {}, "audience": {}},
    }


def _header(text: str) -> dict:
    return {
        "type": "header",
        "value": {"text": text, "design": {}, "audience": {}},
    }


def _rich_text(text: str) -> dict:
    return {
        "type": "rich_text",
        "value": {"text": text, "design": {}, "audience": {}},
    }


def _tag_badges(source: str) -> dict:
    return {
        "type": "tag_badges",
        "value": {
            "source": source,
            "max_items": 8,
            "show_overflow": True,
            "color": "",
            "style": "",
            "size": "",
            "empty_text": "",
            "design": {},
            "audience": {},
        },
    }


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


def _action(action: str, text: str, target: str = "") -> dict:
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


def _feed(name: str) -> dict | None:
    from wagtail_daisIE.feeds.models import Feed  # noqa: PLC0415

    feed = Feed.objects.filter(name=name).first()
    if feed is None:
        return None
    return {"type": "feed", "value": {"feed": feed, "layout": {}}}


def _compact(blocks):
    return _as_stream_data([block for block in blocks if block is not None])


def meeting_template_body():
    return _compact(
        [
            _header("{{ meeting.title }}"),
            _text("{{ meeting.description }}"),
            _text("Type: {{ meeting.meeting_type }}"),
            _text("Price: {{ meeting.price }} {{ meeting.currency }}"),
            _text("Terms: {{ meeting.terms }}"),
            _tag_badges("{{ meeting.tags }}"),
            _button("Book this session", "{{ booking_url }}"),
        ],
    )


def peer_template_body():
    return _compact(
        [
            _header("{{ peer_profile.display_title }}"),
            _text("{{ peer_profile.bio }}"),
            _tag_badges("{{ peer_profile.tags }}"),
            _text("Terms: {{ peer_profile.default_terms }}"),
            _action(
                "bookmark.toggle_peer",
                "Bookmark this care provider",
                "{{ peer_profile.pk }}",
            ),
            _header("Sessions"),
            _feed("sessions"),
            _header("Reviews"),
            _feed("reviews"),
        ],
    )


def review_template_body():
    return _compact(
        [
            _header("Review by {{ review.reviewer.display_name }}"),
            _text("Rating: {{ review.rating }}"),
            _rich_text("{{ review.comment }}"),
            _text("Meeting: {{ review.meeting_request.meeting.title }}"),
            _action(
                "bookmark.toggle_meeting",
                "Bookmark this meeting",
                "{{ review.meeting_request.meeting.pk }}",
            ),
        ],
    )


def user_profile_template_body():
    return _compact(
        [
            _header("{{ user_profile.user.display_name }}"),
            _text("{{ user_profile.bio }}"),
            _tag_badges("{{ user_profile.languages }}"),
        ],
    )


def tag_template_body():
    return _compact(
        [
            _header("{{ tag.name }}"),
            _text("{{ tag.description }}"),
            _feed("sessions"),
        ],
    )


def booking_template_body():
    return _compact(
        [
            _header("{{ booking.display_title }}"),
            _text("Meeting: {{ booking.meeting.title }}"),
            _text("Status: {{ booking.status }}"),
            _text("Amount: {{ booking.total_amount }} {{ booking.currency }}"),
            _text("Payment status: {{ booking.status }}"),
            _button("View receipt", "{{ booking.receipt_url }}"),
        ],
    )


def refund_template_body():
    return _compact(
        [
            _header("{{ refund_request.display_title }}"),
            _text("Reason: {{ refund_request.reason }}"),
            _text("Status: {{ refund_request.status }}"),
            _text("Booking: {{ refund_request.meeting_request.meeting.title }}"),
        ],
    )


TEMPLATE_BODIES = {
    "meeting": meeting_template_body,
    "peer_profile": peer_template_body,
    "review": review_template_body,
    "user_profile": user_profile_template_body,
    "tag": tag_template_body,
    "booking": booking_template_body,
    "refund_request": refund_template_body,
}

__all__ = ["TEMPLATE_BODIES"]
