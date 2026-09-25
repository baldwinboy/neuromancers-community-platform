"""Request-based audience predicates.

Each callable accepts an ``HttpRequest`` and returns ``bool``. Object-level
rules resolve their target from the URL kwargs (``request.daisie_path_params``)
or, as a fallback, the ``?user=`` query parameter. Staff and superusers
short-circuit to ``True`` where a moderator should see everything.

These predicates are plain Python; registering them in
``WAGTAIL_DAISIE_AUDIENCE_RULES`` happens in the daisIE track.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neuromancers_network.peers.services import is_eligible_peer

if TYPE_CHECKING:
    from django.http import HttpRequest

    from neuromancers_network.meetings.models import Meeting
    from neuromancers_network.users.models import User


def _request_user(request: HttpRequest) -> User | None:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


def _is_moderator(user: User | None) -> bool:
    return user is not None and bool(user.is_staff or user.is_superuser)


def _path_params(request: HttpRequest) -> dict:
    if request is None:
        return {}
    params = getattr(request, "daisie_path_params", None)
    if params:
        return dict(params)
    resolver_match = getattr(request, "resolver_match", None)
    kwargs = getattr(resolver_match, "kwargs", None)
    if kwargs:
        return dict(kwargs)
    return {}


def _target_user(request: HttpRequest) -> User | None:
    from neuromancers_network.users.models import User  # noqa: PLC0415

    params = _path_params(request)
    lookup: dict[str, object] = {}
    if "user_pk" in params:
        lookup["pk"] = params["user_pk"]
    elif "username" in params:
        lookup["username"] = params["username"]
    elif "user" in params:
        lookup["pk"] = params["user"]
    else:
        requested = getattr(request, "GET", {}).get("user")
        if not requested:
            return None
        if str(requested).isdigit():
            lookup["pk"] = requested
        else:
            lookup["username"] = requested
    return User.objects.filter(**lookup).first()


def _meeting(request: HttpRequest) -> Meeting | None:
    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415

    params = _path_params(request)
    pk = params.get("meeting_pk") or params.get("pk")
    if not pk:
        return None
    return Meeting.objects.filter(pk=pk).first()


def is_authenticated(request: HttpRequest) -> bool:
    return _request_user(request) is not None


def is_moderator(request: HttpRequest) -> bool:
    return _is_moderator(_request_user(request))


def is_peer(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    return _is_moderator(user) or is_eligible_peer(user)


def is_verified_peer(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    return _is_moderator(user) or bool(getattr(user, "is_verified_peer", False))


def is_peer_owner(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    return _is_moderator(user) or is_eligible_peer(user)


def is_meeting_host(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    if _is_moderator(user):
        return True
    meeting = _meeting(request)
    return meeting is not None and meeting.peer_id == user.pk


def is_meeting_seeker(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    if _is_moderator(user):
        return True
    meeting = _meeting(request)
    if meeting is None:
        return False
    return meeting.requests.filter(support_seeker=user).exists()


def is_meeting_participant(request: HttpRequest) -> bool:
    return is_meeting_host(request) or is_meeting_seeker(request)


def is_own_profile(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    target = _target_user(request)
    return target is not None and target.pk == user.pk


def is_own_profile_or_moderator(request: HttpRequest) -> bool:
    return is_moderator(request) or is_own_profile(request)


def is_bookmark_owner(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    if _is_moderator(user):
        return True
    params = _path_params(request)
    owner_pk = params.get("user_pk") or params.get("bookmark_user_pk")
    if owner_pk is None:
        return is_own_profile(request)
    return owner_pk == user.pk
