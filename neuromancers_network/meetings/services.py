"""Meeting domain services enforcing eligibility and defaults."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _

from neuromancers_network.peers.services import is_eligible_peer
from neuromancers_network.taxonomy.validators import validate_allowed_tags
from neuromancers_network.taxonomy.validators import validate_countries
from neuromancers_network.taxonomy.validators import validate_languages

if TYPE_CHECKING:
    from neuromancers_network.users.models import User

    from .models import Meeting


def default_terms_for(peer: User) -> str:
    """Return the peer's default terms, or an empty string."""
    profile = getattr(peer, "peer_profile", None)
    if profile is None:
        return ""
    return profile.default_terms or ""


def create_meeting(*, peer: User, **fields) -> Meeting:
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
    """Publish *meeting* (draft → published)."""
    meeting.publish()
    meeting.save(validate=False, update_fields=["status", "updated_at"])
    return meeting


def default_access_needs_for(seeker: User) -> str:
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
    from neuromancers_network.peers.models.availability import (  # noqa: PLC0415
        PeerAvailability,
    )
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
    seeker: User,
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
    from .models import MeetingRequest  # noqa: PLC0415

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
    booking = Booking.objects.create(**booking_kwargs)

    for session in sessions or []:
        requested_start = session.get("requested_start_time")
        requested_duration = session.get("requested_duration_minutes")
        _ensure_slot_available(
            meeting,
            _coerce_datetime(requested_start),
            requested_duration,
        )
        request = MeetingRequest(
            meeting=meeting,
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
