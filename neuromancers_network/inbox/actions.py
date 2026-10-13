"""Action handlers for the in-app notification inbox."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import timezone

from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.inbox.models import Notification


def _owned(request, data) -> Notification:
    user = require_authenticated(request)
    pk = data.get("notification") or data.get("pk") or data.get("target")
    return get_object_or_404(Notification, pk=pk, recipient=user)


def notifications_mark_read(request, data):
    notification = _owned(request, data)
    notification.mark_read()
    return redirect_back(request)


def notifications_mark_all_read(request, data):
    user = require_authenticated(request)
    Notification.objects.filter(
        recipient=user,
        read_at__isnull=True,
        deleted_at__isnull=True,
    ).update(read_at=timezone.now())
    return redirect_back(request)


def notifications_delete(request, data):
    notification = _owned(request, data)
    notification.soft_delete()
    return redirect_back(request)
