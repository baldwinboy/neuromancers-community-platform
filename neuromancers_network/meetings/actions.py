"""Action handlers for meeting creation, booking and refunds."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django_fsm import can_proceed

from neuromancers_network.core.actions import as_bool
from neuromancers_network.core.actions import as_list
from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import BookingStatus
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import RefundRequest
from neuromancers_network.meetings.models.booking import (
    create_checkout_session_for_bookings,
)
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.services import create_meeting
from neuromancers_network.meetings.services import default_terms_for
from neuromancers_network.meetings.services import delete_all
from neuromancers_network.meetings.services import delete_meeting
from neuromancers_network.meetings.services import publish_meeting
from neuromancers_network.meetings.services import unpublish_all

logger = logging.getLogger(__name__)

_ALLOWED_MEETING_FIELDS = {
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
}


def _owned_meeting(user, data) -> Meeting:
    pk = (
        data.get("meeting")
        or data.get("meeting_id")
        or data.get("pk")
        or data.get("target")
    )
    meeting = get_object_or_404(Meeting, pk=pk)
    if meeting.peer_id != user.pk and not user.is_moderator:
        message = "You cannot manage this meeting"
        raise PermissionDenied(message)
    return meeting


def meetings_create(request, data):
    user = require_authenticated(request)
    fields = {key: data.get(key) for key in _ALLOWED_MEETING_FIELDS if key in data}
    fields["tags"] = as_list(data, "tags")
    fields["countries"] = as_list(data, "countries")
    fields["languages"] = as_list(data, "languages")
    create_meeting(peer=user, **fields)

    return redirect_back(request)


def meetings_restore_default_terms(request, data):
    user = require_authenticated(request)
    meeting = _owned_meeting(user, data)
    meeting.terms = default_terms_for(meeting.peer)
    meeting.save()
    return redirect_back(request)


def _template_body(templates, selector):
    """Return the body of a named/indexed template, or ``None`` if not found."""
    for index, template in enumerate(templates or []):
        if not isinstance(template, dict):
            continue
        if str(index) == str(selector) or template.get("name") == selector:
            return template.get("body") or ""
    return None


def meetings_apply_terms_template(request, data):
    user = require_authenticated(request)
    meeting = _owned_meeting(user, data)
    profile = getattr(meeting.peer, "peer_profile", None)
    templates = getattr(profile, "terms_templates", []) if profile is not None else []
    body = _template_body(templates, data.get("template"))
    if body is not None:
        meeting.terms = body
        meeting.save(update_fields=["terms", "updated_at"])
    return redirect_back(request)


def meetings_publish(request, data):
    user = require_authenticated(request)
    meeting = _owned_meeting(user, data)
    publish_meeting(meeting)
    return redirect_back(request)


def meetings_unpublish(request, data):
    user = require_authenticated(request)
    meeting = _owned_meeting(user, data)
    meeting.unpublish()
    meeting.save(validate=False, update_fields=["status", "updated_at"])
    return redirect_back(request)


def meetings_archive(request, data):
    user = require_authenticated(request)
    meeting = _owned_meeting(user, data)
    meeting.archive()
    meeting.save(validate=False, update_fields=["status", "updated_at"])
    return redirect_back(request)


def meetings_delete(request, data):
    user = require_authenticated(request)
    meeting = _owned_meeting(user, data)
    delete_meeting(meeting)
    return redirect_back(request)


def meetings_unpublish_all(request, data):
    """Unpublish every published meeting owned by the signed-in peer."""
    user = require_authenticated(request)
    unpublish_all(user)
    return redirect_back(request)


def meetings_delete_all(request, data):
    """Delete every meeting owned by the signed-in peer."""
    user = require_authenticated(request)
    delete_all(user)
    return redirect_back(request)


def bookings_request(request, data):
    """Create a booking (and its sessions) for the signed-in seeker."""
    user = require_authenticated(request)
    meeting_pk = data.get("meeting") or data.get("meeting_id")
    meeting = get_object_or_404(Meeting, pk=meeting_pk)

    access_needs = data.get("access_needs")
    template_key = data.get("access_needs_template")
    if template_key not in (None, ""):
        profile = getattr(user, "user_profile", None)
        templates = getattr(profile, "access_needs_templates", []) if profile else []
        body = _template_body(templates, template_key)
        if body is not None:
            access_needs = body

    session = {
        "requested_start_time": data.get("requested_start_time"),
        "requested_duration_minutes": data.get("requested_duration_minutes")
        or meeting.duration_minutes,
    }
    sessions = [session] if session["requested_start_time"] else []
    create_booking(
        meeting=meeting,
        seeker=user,
        sessions=sessions,
        access_needs=access_needs,
        peer_terms=data.get("peer_terms") or meeting.terms,
        terms_accepted=as_bool(data.get("agree_to_terms")),
    )
    return redirect_back(request)


def bookings_checkout(request, data):
    """Create a Stripe Checkout session for a booking and redirect to it."""
    user = require_authenticated(request)
    booking = get_object_or_404(
        Booking,
        pk=data.get("booking") or data.get("booking_id"),
    )
    if booking.support_seeker_id != user.pk and not user.is_moderator:
        message = "You cannot pay for this booking"
        raise PermissionDenied(message)
    checkout_url = booking.create_checkout_session(request)
    return redirect(checkout_url)


def bookings_checkout_many(request, data):
    """Create one Checkout Session per peer for the selected unpaid bookings."""
    user = require_authenticated(request)
    ids = as_list(data, "bookings") or as_list(data, "booking_ids")
    if not ids:
        ids = as_list(data, "booking")
    bookings = list(
        Booking.objects.filter(
            pk__in=ids,
            support_seeker=user,
            status=BookingStatus.PENDING,
        ).select_related("meeting"),
    )
    if not bookings:
        message = "No unpaid bookings were selected"
        raise PermissionDenied(message)
    peer_ids = {booking.meeting.peer_id for booking in bookings}
    currencies = {booking.meeting.currency.upper() for booking in bookings}
    if len(peer_ids) > 1:
        messages.error(
            request,
            _("Please pay for bookings from one care provider at a time."),
        )
        return redirect_back(request)
    if len(currencies) > 1:
        messages.error(
            request,
            _("Please pay for bookings in one currency at a time."),
        )
        return redirect_back(request)
    try:
        checkout_url = create_checkout_session_for_bookings(bookings, request)
    except ValueError as exc:
        logger.warning("Could not start checkout for user %s: %s", user.pk, exc)
        messages.error(
            request,
            _(
                "We could not start checkout for these bookings. "
                "Please try again or contact support.",
            ),
        )
        return redirect_back(request)
    return redirect(checkout_url)


def _host_request(user, data) -> MeetingRequest:
    pk = (
        data.get("meeting_request")
        or data.get("meeting_request_id")
        or data.get("target")
        or data.get("pk")
    )
    meeting_request = get_object_or_404(MeetingRequest, pk=pk)
    if meeting_request.meeting.peer_id != user.pk and not user.is_moderator:
        message = "You cannot manage this booking"
        raise PermissionDenied(message)
    return meeting_request


def _host_refund(user, data) -> RefundRequest:
    pk = (
        data.get("refund_request")
        or data.get("refund_request_id")
        or data.get("target")
        or data.get("pk")
    )
    refund_request = get_object_or_404(RefundRequest, pk=pk)
    if (
        refund_request.meeting_request.meeting.peer_id != user.pk
        and not user.is_moderator
    ):
        message = "You cannot manage this refund"
        raise PermissionDenied(message)
    return refund_request


def bookings_approve(request, data):
    user = require_authenticated(request)
    meeting_request = _host_request(user, data)
    if not can_proceed(meeting_request.approve):
        message = "This booking cannot be approved"
        raise PermissionDenied(message)
    meeting_request.approve()
    meeting_request.save()
    return redirect_back(request)


def bookings_reject(request, data):
    user = require_authenticated(request)
    meeting_request = _host_request(user, data)
    if not can_proceed(meeting_request.reject):
        message = "This booking cannot be rejected"
        raise PermissionDenied(message)
    meeting_request.reject()
    meeting_request.save()
    return redirect_back(request)


def bookings_revoke(request, data):
    user = require_authenticated(request)
    meeting_request = _host_request(user, data)
    if meeting_request.status == MeetingRequestStatus.PAID:
        meeting_request.request_refund(data.get("reason") or "Revoked by host")
    if can_proceed(meeting_request.cancel):
        meeting_request.cancel()
        meeting_request.save()
    return redirect_back(request)


def refunds_approve(request, data):
    user = require_authenticated(request)
    refund_request = _host_refund(user, data)
    if not can_proceed(refund_request.approve):
        message = "This refund cannot be approved"
        raise PermissionDenied(message)
    refund_request.approve(amount=data.get("amount") or None)
    refund_request.save()
    return redirect_back(request)


def refunds_reject(request, data):
    user = require_authenticated(request)
    refund_request = _host_refund(user, data)
    if not can_proceed(refund_request.reject):
        message = "This refund cannot be rejected"
        raise PermissionDenied(message)
    refund_request.reject()
    refund_request.save()
    return redirect_back(request)


def bookings_request_refund(request, data):
    """Raise a refund request against one of the seeker's paid sessions."""
    user = require_authenticated(request)
    meeting_request = get_object_or_404(
        MeetingRequest,
        pk=data.get("meeting_request") or data.get("meeting_request_id"),
    )
    if meeting_request.support_seeker_id != user.pk and not user.is_moderator:
        message = "You cannot request a refund for this booking"
        raise PermissionDenied(message)
    meeting_request.request_refund(
        data.get("reason", ""),
        amount=data.get("amount") or None,
    )
    return redirect_back(request)
