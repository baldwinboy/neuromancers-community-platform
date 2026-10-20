# ruff: noqa: PLC0415
"""Viewer-scoped visibility for user-owned records and generated detail pages.

Feeds (selectors, APIs, the search page) and the ``before_serve_page`` guard
both derive their answer from this module so the two layers cannot drift.

The rule has three parts, each reusing an existing primitive:

- **published state** — read from ``WAGTAIL_DAISIE_DETAIL_PAGES``'s
  ``publish_field``, the same field the detail-page bridge uses. This is what
  stops an unpublished meeting (or an unapproved review/profile) being served.
- **owner eligibility** — reuses :func:`peers.services.is_eligible_peer`, which
  already folds in a deactivated account, a paused/ended plan, KYC and
  verification requirements.
- **pairwise blocks** — :func:`hidden_user_ids`, symmetric for both parties.

Imports are deferred to call time so this module can be imported from any app
without introducing a cycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models import Q

if TYPE_CHECKING:
    from django.db.models import QuerySet

#: Owner requirement per detail type.
#: - ``eligible_peer``: owner must satisfy the peer requirements (approved +
#:   active plan + KYC/verification). A paused/ended plan hides the page.
#: - ``active_visible``: owner must merely be active; profile visibility decides
#:   who may see it.
#: Types absent from this map impose no owner requirement (e.g. tags).
_OWNER_POLICY = {
    "meeting": "eligible_peer",
    "peer_profile": "eligible_peer",
    "review": "eligible_peer",
    "user_profile": "active_visible",
    "tag": None,
}


def _is_moderator(user) -> bool:
    """Whether *user* is staff/superuser (sees everything)."""
    return bool(getattr(user, "is_moderator", False))


def _is_authenticated(user) -> bool:
    return bool(getattr(user, "is_authenticated", False))


def hidden_user_ids(viewer) -> set[int]:
    """IDs hidden from *viewer* by a pairwise block (symmetric).

    Includes both the members *viewer* blocked and the members who blocked
    *viewer*: a block hides each party's content from the other.
    """
    if not _is_authenticated(viewer):
        return set()
    from neuromancers_network.moderation.models import UserBlock

    hidden = set()
    viewer_pk = viewer.pk
    rows = UserBlock.objects.filter(
        Q(blocker=viewer) | Q(blocked=viewer),
    ).values_list("blocker_id", "blocked_id")
    for blocker_id, blocked_id in rows:
        if blocker_id == viewer_pk:
            hidden.add(blocked_id)
        if blocked_id == viewer_pk:
            hidden.add(blocker_id)
    return hidden


def is_blocked_pair(viewer, owner) -> bool:
    """Whether *viewer* and *owner* have a block in either direction."""
    if owner is None or not _is_authenticated(viewer):
        return False
    owner_pk = getattr(owner, "pk", None)
    if owner_pk is None:
        return False
    return owner_pk in hidden_user_ids(viewer)


def source_participant_ids(source) -> set[int]:
    """Return the member IDs allowed to see a two-party *source*.

    Bookings are visible to the seeker and the meeting's peer; refund requests
    to the request's seeker and the meeting's peer. Other sources have none.
    """
    if source is None:
        return set()
    from neuromancers_network.meetings.models import Booking
    from neuromancers_network.meetings.models import RefundRequest

    if isinstance(source, Booking):
        ids = {source.support_seeker_id, source.meeting.peer_id}
    elif isinstance(source, RefundRequest):
        request = source.meeting_request
        ids = {request.support_seeker_id, request.meeting.peer_id}
    else:
        return set()
    return {pk for pk in ids if pk is not None}


def source_owner(source):
    """Return the member who owns *source*, or ``None``.

    Mapping: a user is its own owner; a ``PeerProfile`` is owned by ``.user``;
    a ``Meeting``/``Review`` is owned by ``.peer`` (for a review, the reviewed
    peer); a ``Tag`` has no owner.
    """
    if source is None:
        return None
    if isinstance(source, AbstractBaseUser):
        return source
    user = getattr(source, "user", None)
    if isinstance(user, AbstractBaseUser):
        return user
    peer = getattr(source, "peer", None)
    if isinstance(peer, AbstractBaseUser):
        return peer
    return None


def _detail_config(source):
    from wagtail_daisIE.detail_pages.registry import detail_page_for_instance

    return detail_page_for_instance(source)


def source_is_public(source) -> bool:
    """Whether *source* is in its published state.

    Uses the detail-page registry's ``publish_field`` (``is_live`` for
    meetings/profiles/reviews, ``is_active`` for tags). Types with no
    ``publish_field`` are always public.
    """
    if source is None:
        return True
    config = _detail_config(source)
    if config is None or not config.publish_field:
        return True
    return bool(getattr(source, config.publish_field, False))


def _owner_policy(source) -> str | None:
    config = _detail_config(source)
    if config is None:
        return None
    return _OWNER_POLICY.get(config.key)


def _active_visible(owner, viewer) -> bool:
    """Active account whose profile visibility admits *viewer*."""
    from neuromancers_network.users.models.choices import ProfileVisibility

    if not getattr(owner, "is_active", False) or getattr(
        owner,
        "is_deactivated",
        False,
    ):
        return False
    profile = getattr(owner, "user_profile", None)
    visibility = getattr(profile, "visibility", ProfileVisibility.MEMBERS)
    if visibility == ProfileVisibility.PUBLIC:
        return True
    if visibility == ProfileVisibility.MEMBERS:
        return _is_authenticated(viewer)
    return False  # PRIVATE — owner and moderators only (handled by the caller).


def viewer_can_view_source(source, viewer) -> bool:  # noqa: PLR0911
    """Whether *viewer* may see the detail page for *source*.

    Moderators and the owner always may. Everyone else is bound by the source's
    published state, the owner's eligibility/visibility, and pairwise blocks.
    """
    if source is None:
        return True
    if _is_moderator(viewer):
        return True
    participants = source_participant_ids(source)
    if participants:
        return _is_authenticated(viewer) and viewer.pk in participants
    owner = source_owner(source)
    if owner is None:
        return source_is_public(source)
    if viewer is not None and getattr(viewer, "pk", None) == owner.pk:
        return True
    if not source_is_public(source):
        return False
    if is_blocked_pair(viewer, owner):
        return False
    policy = _owner_policy(source)
    if policy == "eligible_peer":
        from neuromancers_network.peers.services import is_eligible_peer

        return is_eligible_peer(owner)
    if policy == "active_visible":
        return _active_visible(owner, viewer)
    return True


def exclude_hidden(queryset: QuerySet, viewer, *, owner_field: str) -> QuerySet:
    """Exclude rows owned by members in a pairwise block with *viewer*.

    *owner_field* is the queryset lookup to the owning member (e.g. ``"peer"``
    from ``Meeting``, ``"user"`` from ``PeerProfile``).
    """
    ids = hidden_user_ids(viewer)
    if not ids:
        return queryset
    return queryset.exclude(**{f"{owner_field}__in": ids})
