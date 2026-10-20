"""Meeting domain services enforcing eligibility and defaults."""

from __future__ import annotations

import logging
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _
from django_fsm import can_proceed

from neuromancers_network.peers.services import is_eligible_peer
from neuromancers_network.taxonomy.validators import validate_allowed_tags
from neuromancers_network.taxonomy.validators import validate_countries
from neuromancers_network.taxonomy.validators import validate_languages

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from .models import Meeting

logger = logging.getLogger(__name__)


def default_terms_for(peer: AbstractBaseUser) -> str:
    """Return the peer's default terms, or an empty string."""
    profile = getattr(peer, "peer_profile", None)
    if profile is None:
        return ""
    return profile.default_terms or ""


def create_meeting(*, peer: AbstractBaseUser, **fields) -> Meeting:
    """Create a meeting for *peer*, seeding terms from the peer's defaults."""
    from .models import Meeting  # noqa: PLC0415

    if not is_eligible_peer(peer):
        message = "Peer is not eligible to create meetings"
        raise PermissionDenied(message)

    tags = fields.pop("tags", None)
    countries = fields.pop("countries", None)
    languages = fields.pop("languages", None)
    fields.setdefault("terms", default_terms_for(peer))
    meeting = Meeting(peer=peer, **fields)
    meeting.save()
    if tags is not None:
        meeting.tags.set(validate_allowed_tags(tags))
    if countries is not None:
        meeting.countries.set(validate_countries(countries))
    if languages is not None:
        meeting.languages.set(validate_languages(languages))
    return meeting


def publish_meeting(meeting: Meeting) -> Meeting:
    """Publish *meeting* after enforcing terms and the provider agreement."""
    if not (meeting.terms or "").strip():
        message = _("Add meeting terms before publishing.")
        raise ValidationError(message)

    profile = getattr(meeting.peer, "peer_profile", None)
    if profile is None or not profile.has_accepted_provider_agreement:
        message = _("Accept the care provider agreement before publishing.")
        raise PermissionDenied(message)

    meeting.publish()
    meeting.save(validate=False, update_fields=["status", "updated_at"])
    return meeting


def unpublish_all(peer) -> int:
    """Unpublish every currently published meeting owned by *peer*."""
    from .models import Meeting  # noqa: PLC0415
    from .models import MeetingStatus  # noqa: PLC0415

    unpublished = 0
    meetings = Meeting.objects.filter(peer=peer, status=MeetingStatus.PUBLISHED)
    for meeting in meetings:
        meeting.unpublish()
        meeting.save(validate=False, update_fields=["status", "updated_at"])
        unpublished += 1
    return unpublished


def delete_all(peer) -> int:
    """Delete every meeting owned by *peer*. Returns the number deleted."""
    from .models import Meeting  # noqa: PLC0415

    meetings = Meeting.objects.filter(peer=peer)
    deleted = meetings.count()
    cancel_and_refund_for_peer(peer)
    meetings.delete()
    return deleted


def delete_meeting(meeting) -> None:
    """Cancel/refund a meeting's active sessions, then delete the meeting."""
    cancel_and_refund_for_meeting(meeting)
    meeting.delete()


def _cancel_and_refund_requests(requests, reason: str) -> int:
    """Cancel active requests, requesting refunds for paid ones.

    Refunds follow the meeting's approval policy (auto-issued or left pending
    for review); a Stripe failure is logged and never blocks the cancellation.
    Cancelling emits the existing ``booking_cancelled`` notification.
    """
    from .models import MeetingRequestStatus  # noqa: PLC0415

    cancelled = 0
    for request in requests:
        if request.status == MeetingRequestStatus.PAID:
            try:
                request.request_refund(reason)
            except Exception:
                logger.exception(
                    "Failed to request refund for meeting request %s",
                    request.pk,
                )
        if can_proceed(request.cancel):
            request.cancel()
            request.save(validate=False, update_fields=["status", "updated_at"])
            cancelled += 1
    return cancelled


def _active_requests(**filters):
    from .models import MeetingRequest  # noqa: PLC0415
    from .models import MeetingRequestStatus  # noqa: PLC0415

    return (
        MeetingRequest.objects.filter(**filters)
        .exclude(
            status__in=[
                MeetingRequestStatus.CANCELLED,
                MeetingRequestStatus.COMPLETED,
                MeetingRequestStatus.REJECTED,
            ],
        )
        .select_related("meeting")
    )


def cancel_and_refund_for_peer(peer) -> int:
    """Cancel a peer's active bookings and request refunds for paid sessions.

    Used when a peer withdraws (deactivation/deletion).
    """
    return _cancel_and_refund_requests(
        _active_requests(meeting__peer=peer),
        "Care provider is no longer available",
    )


def cancel_and_refund_for_meeting(meeting) -> int:
    """Cancel a meeting's active bookings and request refunds for paid sessions."""
    return _cancel_and_refund_requests(
        _active_requests(meeting=meeting),
        "The meeting was cancelled",
    )


def default_access_needs_for(seeker: AbstractBaseUser) -> str:
    """Return the seeker's profile-level access needs, if any."""
    profile = getattr(seeker, "user_profile", None)
    if profile is None:
        return ""
    return profile.access_needs or ""


def _coerce_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    parsed = parse_datetime(str(value))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def _ensure_slot_available(meeting: Meeting, start, duration_minutes) -> None:
    """Reject a 1:1 slot that falls outside the peer's availability.

    Peers with no availability windows configured are unrestricted (opt-in).
    Containment also excludes times already booked, so approved requests cannot
    be double-booked.
    """
    from neuromancers_network.peers.models.availability import PeerAvailability  # noqa: PLC0415
    from neuromancers_network.peers.services import available_slots  # noqa: PLC0415

    from .models import MeetingType  # noqa: PLC0415

    if meeting.meeting_type != MeetingType.ONE_ON_ONE or start is None:
        return
    if not duration_minutes:
        return
    if not PeerAvailability.objects.filter(peer=meeting.peer).exists():
        return

    end = start + timedelta(minutes=int(duration_minutes))
    slots = available_slots(meeting.peer, until=end)
    if not any(
        slot_start <= start and end <= slot_end for slot_start, slot_end in slots
    ):
        raise ValidationError(
            {
                "requested_start_time": _(
                    "The requested time is outside the care provider's availability.",
                ),
            },
        )


def create_booking(  # noqa: PLR0913
    *,
    meeting: Meeting,
    seeker: AbstractBaseUser,
    sessions=None,
    access_needs: str | None = None,
    peer_terms: str = "",
    terms_accepted: bool = False,
    status=None,
):
    """Create a booking for *seeker* with one or more session requests.

    Enforces the two-way disclosure contract: a seeker fulfils their access
    needs (defaulting to their profile) and, when the meeting carries terms,
    must accept them with a non-empty snapshot.
    """
    from .models import Booking  # noqa: PLC0415
    from .models import Meeting as MeetingModel  # noqa: PLC0415
    from .models import MeetingRequest  # noqa: PLC0415

    if not is_eligible_peer(meeting.peer):
        message = _("This care provider is not currently available for bookings.")
        raise ValidationError(message)

    from neuromancers_network.moderation.visibility import is_blocked_pair  # noqa: PLC0415

    if is_blocked_pair(seeker, meeting.peer):
        message = _("This care provider is not available for bookings.")
        raise ValidationError(message)

    if access_needs is None:
        access_needs = default_access_needs_for(seeker)

    agreed_terms = (peer_terms or "").strip() or meeting.terms
    if meeting.terms and not (terms_accepted and agreed_terms.strip()):
        message = _("The meeting terms must be accepted to book.")
        raise ValidationError(message)

    accepted_at = timezone.now() if terms_accepted else None

    booking_kwargs = {
        "meeting": meeting,
        "support_seeker": seeker,
        "currency": meeting.currency,
        "access_needs": access_needs,
    }
    if status is not None:
        booking_kwargs["status"] = status

    with transaction.atomic():
        locked = MeetingModel.objects.select_for_update().get(pk=meeting.pk)
        if locked.is_fully_booked:
            message = _("This meeting is fully booked.")
            raise ValidationError(message)
        booking_kwargs["meeting"] = locked
        booking = Booking.objects.create(**booking_kwargs)

        for session in sessions or []:
            requested_start = session.get("requested_start_time")
            requested_duration = session.get("requested_duration_minutes")
            _ensure_slot_available(
                locked,
                _coerce_datetime(requested_start),
                requested_duration,
            )
            request = MeetingRequest(
                meeting=locked,
                support_seeker=seeker,
                booking=booking,
                requested_start_time=requested_start,
                requested_duration_minutes=requested_duration,
                access_needs=session.get("access_needs", access_needs),
                peer_terms=agreed_terms,
                terms_accepted=terms_accepted,
                terms_accepted_at=accepted_at,
            )
            request.start()
            request.save()
    return booking


def sync_meeting_durations(meeting: Meeting, durations: list[int]) -> None:
    """Reconcile a 1:1 meeting's price tiers with the given *durations*.

    Existing tiers are retained (preserving their price options); tiers whose
    duration is no longer offered are removed, and new durations gain an empty
    tier ready for pricing.
    """
    from .models import MeetingPriceTier  # noqa: PLC0415

    desired = set(durations)
    existing = {tier.duration_minutes: tier for tier in meeting.price_tiers.all()}

    for duration in sorted(desired - existing.keys()):
        MeetingPriceTier.objects.create(meeting=meeting, duration_minutes=duration)

    stale = existing.keys() - desired
    if stale:
        meeting.price_tiers.filter(duration_minutes__in=stale).delete()


def apply_duration_tiers(meeting: Meeting, rows) -> None:
    """Reconcile a 1:1 meeting's tiers and their default price from *rows*.

    *rows* is a list of ``{"duration_minutes": int, "amount": Decimal | None}``
    (as produced by ``meetings.tier_fields.DurationTiersField``). Each row's
    ``amount`` becomes the tier's default price option; a missing amount clears
    the tier's options.
    """
    from .models import MeetingPriceOption  # noqa: PLC0415

    durations = [
        int(row["duration_minutes"])
        for row in rows
        if row.get("duration_minutes") is not None
    ]
    sync_meeting_durations(meeting, durations)

    for row in rows:
        minutes = row.get("duration_minutes")
        if minutes is None:
            continue
        tier = meeting.price_tiers.filter(duration_minutes=int(minutes)).first()
        if tier is None:
            continue
        amount = row.get("amount")
        if amount in (None, ""):
            tier.options.all().delete()
            continue
        option = tier.options.filter(is_default=True).first()
        if option is None:
            MeetingPriceOption.objects.create(
                tier=tier,
                amount=Decimal(str(amount)),
                is_default=True,
            )
        else:
            option.amount = Decimal(str(amount))
            option.save(update_fields=["amount", "updated_at"])
