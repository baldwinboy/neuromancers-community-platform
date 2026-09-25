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


HANDLERS = {
    "profile.edit": profile_edit,
    "profile.save_access_needs": profile_save_access_needs,
    "profile.save_visibility": profile_save_visibility,
    "profile.save_notification_preferences": profile_save_notification_preferences,
}
