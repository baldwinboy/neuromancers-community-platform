"""Object-level permissions for meetings and user profiles (django-rules).

Predicates take ``(user, obj=None)`` so they work both as flat permissions
(``has_perm(user, "meetings.add_meeting")``) and object permissions
(``has_perm(user, "meetings.change_meeting", meeting)``).
"""

from __future__ import annotations

from rules import add_perm
from rules.predicates import predicate

from neuromancers_network.peers.services import is_eligible_peer


@predicate
def is_moderator(user, obj=None) -> bool:
    return bool(user.is_staff or user.is_superuser)


@predicate
def is_peer(user, obj=None) -> bool:
    return bool(is_eligible_peer(user))


@predicate
def is_meeting_host(user, obj=None) -> bool:
    return obj is not None and getattr(obj, "peer_id", None) == user.pk


@predicate
def is_meeting_participant(user, obj=None) -> bool:
    if obj is None:
        return False
    if getattr(obj, "peer_id", None) == user.pk:
        return True
    requests = getattr(obj, "requests", None)
    if requests is None:
        return False
    return requests.filter(support_seeker=user).exists()


@predicate
def is_own_profile(user, obj=None) -> bool:
    return obj is not None and getattr(obj, "pk", None) == user.pk


add_perm("meetings.add_meeting", is_peer | is_moderator)
add_perm("meetings.change_meeting", is_moderator | is_meeting_host)
add_perm(
    "meetings.view_meeting",
    is_moderator | is_meeting_host | is_meeting_participant,
)
add_perm("users.change_user", is_own_profile | is_moderator)
