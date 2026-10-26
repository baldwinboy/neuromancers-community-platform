"""Action handlers for member-initiated account deletion and blocking."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.moderation.blocking import block_user
from neuromancers_network.moderation.blocking import unblock_user
from neuromancers_network.moderation.export import request_data_export
from neuromancers_network.moderation.services import request_account_deletion


def account_delete_request(request, data):
    """Request deletion of the signed-in member's own account."""
    from neuromancers_network.core.audience import can_delete_account  # noqa: PLC0415

    user = require_authenticated(request)
    if not can_delete_account(request):
        message = "This account cannot request deletion"
        raise PermissionDenied(message)
    reason = data.get("reason", "") if hasattr(data, "get") else ""
    request_account_deletion(user, actor=user, request=request, reason=reason)
    return redirect_back(request)


def _block_target(data):
    target = None
    if hasattr(data, "get"):
        target = (
            data.get("user")
            or data.get("user_id")
            or data.get("blocked")
            or data.get("target")
        )
    return get_object_or_404(get_user_model(), pk=target)


def user_block(request, data):
    """Block another member."""
    actor = require_authenticated(request)
    blocked = _block_target(data)
    reason = data.get("reason", "") if hasattr(data, "get") else ""
    block_user(actor, blocked, request=request, reason=reason)
    return redirect_back(request)


def user_unblock(request, data):
    """Unblock a previously blocked member."""
    actor = require_authenticated(request)
    blocked = _block_target(data)
    unblock_user(actor, blocked, request=request)
    return redirect_back(request)


def data_export_request(request, data):
    """Queue a copy of the signed-in member's data."""
    from neuromancers_network.core.audience import can_request_data_export  # noqa: PLC0415

    user = require_authenticated(request)
    if not can_request_data_export(request):
        message = "A data export is already in progress or was recently created"
        raise PermissionDenied(message)
    try:
        request_data_export(user)
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect_back(request)
