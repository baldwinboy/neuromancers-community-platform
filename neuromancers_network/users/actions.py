"""Action handlers for profile editing and disclosure preferences."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from neuromancers_network.core.actions import as_bool
from neuromancers_network.core.actions import as_list
from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.users.models import ProfileVisibility
from neuromancers_network.users.models import UserProfile


def _profile_for(user) -> UserProfile:
    profile, _created = UserProfile.objects.get_or_create(user=user)
    return profile


def profile_edit(request, data):
    user = require_authenticated(request)
    profile = _profile_for(user)
    if "bio" in data:
        profile.bio = data.get("bio", "")
    if "access_needs" in data:
        profile.access_needs = data.get("access_needs", "")
    if "visibility" in data:
        visibility = data.get("visibility")
        if visibility not in ProfileVisibility.values:
            message = "Unknown visibility"
            raise PermissionDenied(message)
        profile.visibility = visibility
    profile.save()
    return redirect_back(request)


def profile_save_access_needs(request, data):
    user = require_authenticated(request)
    profile = _profile_for(user)
    profile.access_needs = data.get("access_needs", "")
    if "access_needs_visible_to_peer" in data:
        profile.access_needs_visible_to_peer = as_bool(
            data.get("access_needs_visible_to_peer"),
        )
    profile.save()
    return redirect_back(request)


def profile_save_visibility(request, data):
    user = require_authenticated(request)
    visibility = data.get("visibility")
    if visibility not in ProfileVisibility.values:
        message = "Unknown visibility"
        raise PermissionDenied(message)
    profile = _profile_for(user)
    profile.visibility = visibility
    profile.save()
    return redirect_back(request)


def profile_save_notification_preferences(request, data):
    """Persist the member's notification opt-out list."""
    from neuromancers_network.inbox.models import (  # noqa: PLC0415
        NotificationPreference,
    )

    user = require_authenticated(request)
    preference, _created = NotificationPreference.objects.get_or_create(user=user)
    preference.disabled_event_types = as_list(data, "disabled_event_types")
    preference.save()
    return redirect_back(request)


def accept_tos(request, data):
    """Record that the signed-in member has accepted the Terms and Conditions."""
    user = require_authenticated(request)
    if not user.accepted_tos:
        user.accepted_tos = True
        user.save(update_fields=["accepted_tos"])
    return redirect_back(request)


def _lifecycle_target(actor, data):
    """Return the user to act on: the actor, or a moderator-chosen target."""
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    target = None
    if hasattr(data, "get"):
        target = data.get("user") or data.get("user_id") or data.get("target")
    if not target or str(target) == str(actor.pk):
        return actor
    if not actor.is_moderator:
        message = "You cannot manage this account"
        raise PermissionDenied(message)
    user_model = get_user_model()
    user = user_model.objects.filter(pk=target).first()
    if user is None:
        message = "Unknown account"
        raise PermissionDenied(message)
    return user


def account_deactivate(request, data):
    """Deactivate the member's own account, or a target as a moderator."""
    from neuromancers_network.users.services import deactivate_account  # noqa: PLC0415

    actor = require_authenticated(request)
    target = _lifecycle_target(actor, data)
    reason = data.get("reason", "") if hasattr(data, "get") else ""
    deactivate_account(target, actor=actor, request=request, reason=reason)
    return redirect_back(request)


def account_reactivate(request, data):
    """Reactivate the member's own account, or a target as a moderator."""
    from neuromancers_network.users.services import reactivate_account  # noqa: PLC0415

    actor = require_authenticated(request)
    target = _lifecycle_target(actor, data)
    reactivate_account(target, actor=actor, request=request)
    return redirect_back(request)


def account_revoke_sessions(request, data):
    """Sign the member out of every device."""
    from neuromancers_network.users.sessions import revoke_sessions  # noqa: PLC0415

    user = require_authenticated(request)
    revoke_sessions(user)
    return redirect_back(request)


def account_revoke_other_sessions(request, data):
    """Sign the member out of every device except this one."""
    from neuromancers_network.users.sessions import revoke_sessions  # noqa: PLC0415

    user = require_authenticated(request)
    current = getattr(getattr(request, "session", None), "session_key", None)
    revoke_sessions(user, keep_current=current)
    return redirect_back(request)
