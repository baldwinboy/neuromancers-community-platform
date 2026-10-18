"""Shared allowlists for meeting create/edit inputs."""

from __future__ import annotations

MEETING_FORM_FIELDS = (
    "title",
    "description",
    "terms",
    "meeting_type",
    "meeting_link",
    "pricing_type",
    "price",
    "sliding_scale_min",
    "sliding_scale_max",
    "currency",
    "approval_policy",
    "refund_requires_approval",
    "max_participants",
    "scheduled_at",
    "duration_minutes",
)
