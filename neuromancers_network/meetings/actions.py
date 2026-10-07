"""Action handlers for meeting creation, booking and refunds."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect

from neuromancers_network.core.actions import as_bool
from neuromancers_network.core.actions import as_list
from neuromancers_network.core.actions import redirect_back
from neuromancers_network.core.actions import require_authenticated
from neuromancers_network.meetings.models import Booking
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.services import create_meeting
from neuromancers_network.meetings.services import default_terms_for

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
    pk = data.get("meeting") or data.get("meeting_id") or data.get("pk")
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
    meeting = create_meeting(peer=user, **fields)

    language_ids = as_list(data, "languages")
    if language_ids:
        meeting.languages.set(language_ids)

    return redirect_back(request)


def meetings_restore_default_terms(request, data):
    user = require_authenticated(request)
    meeting = _owned_meeting(user, data)
    meeting.terms = default_terms_for(meeting.peer)
    meeting.save()
    return redirect_back(request)


def bookings_request(request, data):
    """Create a booking (and its sessions) for the signed-in seeker."""
    user = require_authenticated(request)
    meeting_pk = data.get("meeting") or data.get("meeting_id")
    meeting = get_object_or_404(Meeting, pk=meeting_pk)

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
        access_needs=data.get("access_needs"),
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
    meeting_request.request_refund(data.get("reason", ""))
    return redirect_back(request)


HANDLERS = {
    "meetings.create": meetings_create,
    "meetings.restore_default_terms": meetings_restore_default_terms,
    "bookings.request": bookings_request,
    "bookings.checkout": bookings_checkout,
    "bookings.request_refund": bookings_request_refund,
}
