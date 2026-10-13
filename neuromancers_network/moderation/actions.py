"""Action handlers for member-initiated account deletion."""

from __future__ import annotations

from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.moderation.services import cancel_account_deletion
from neuromancers_network.moderation.services import request_account_deletion


def account_delete_request(request, data):
    """Request deletion of the signed-in member's own account."""
    user = require_authenticated(request)
    reason = data.get("reason", "") if hasattr(data, "get") else ""
    request_account_deletion(user, actor=user, request=request, reason=reason)
    return redirect_back(request)


def account_delete_cancel(request, data):
    """Cancel a pending deletion of the signed-in member's own account."""
    user = require_authenticated(request)
    cancel_account_deletion(user, actor=user, request=request)
    return redirect_back(request)


HANDLERS = {
    "account.delete_request": account_delete_request,
    "account.delete_cancel": account_delete_cancel,
}
