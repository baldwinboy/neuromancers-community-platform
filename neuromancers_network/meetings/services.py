"""Meeting domain services enforcing eligibility and defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from neuromancers_network.peers.services import is_eligible_peer
from neuromancers_network.taxonomy.validators import validate_allowed_tags
from neuromancers_network.taxonomy.validators import validate_countries

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
    fields.setdefault("terms", default_terms_for(peer))
    meeting = Meeting(peer=peer, **fields)
    meeting.save()
    if tags is not None:
        meeting.tags.set(validate_allowed_tags(tags))
    if countries is not None:
        meeting.countries.set(validate_countries(countries))
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
        MeetingRequest.objects.create(
            meeting=meeting,
            support_seeker=seeker,
            booking=booking,
            requested_start_time=session.get("requested_start_time"),
            requested_duration_minutes=session.get("requested_duration_minutes"),
            access_needs=session.get("access_needs", access_needs),
            peer_terms=agreed_terms,
            terms_accepted=terms_accepted,
            terms_accepted_at=accepted_at,
        )
    return booking
