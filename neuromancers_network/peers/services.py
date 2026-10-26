"""Peer eligibility rules and 1:1 availability slot expansion."""

from __future__ import annotations

import calendar
import logging
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db.models import Q
from django.utils import timezone
from djstripe.enums import SubscriptionStatus

from neuromancers_network.peers.models.availability import PeerAvailability
from neuromancers_network.peers.models.choices import AvailabilityOccurrence
from neuromancers_network.peers.models.settings import PeerRequirementsSettings

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator

    from neuromancers_network.users.models import User as UserType

logger = logging.getLogger(__name__)

MAX_RECURRENCE_OCCURRENCES = 500


def peer_requirements() -> PeerRequirementsSettings:
    """Return the admin-configured peer requirements (creating defaults)."""
    return PeerRequirementsSettings.load()


def eligibility_failures(user: UserType) -> list[str]:
    """Return the reasons *user* is not (yet) an eligible peer."""
    failures: list[str] = []

    if not getattr(user, "is_active", True):
        failures.append("deactivated")

    profile = getattr(user, "peer_profile", None)
    if profile is None or not profile.is_approved:
        failures.append("not_approved")

    requirements = peer_requirements()
    payment = getattr(user, "payment_profile", None)

    if requirements.require_subscription and not (
        payment is not None and payment.has_active_subscription
    ):
        failures.append("no_active_subscription")

    if requirements.require_kyc and not (payment is not None and payment.kyc_completed):
        failures.append("kyc_incomplete")

    if requirements.require_verification_to_publish and not (
        profile is not None and profile.is_verified
    ):
        failures.append("not_verified")

    return failures


def is_eligible_peer(user: UserType | None) -> bool:
    """Whether *user* is approved and meets the configured peer requirements."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return not eligibility_failures(user)


def eligible_peer_q(prefix: str = "") -> Q:
    """Return a ``Q`` selecting users who meet the peer requirements.

    Mirrors :func:`eligibility_failures` for queryset filtering. *prefix* is
    prepended to every lookup so callers can filter related models, e.g.
    ``"peer__"`` from ``Meeting`` or ``"user__"`` from ``PeerProfile``.
    """
    requirements = peer_requirements()
    query = Q(**{f"{prefix}peer_profile__is_approved": True})
    query &= Q(**{f"{prefix}is_active": True})
    if requirements.require_kyc:
        query &= Q(**{f"{prefix}payment_profile__kyc_completed": True})
    if requirements.require_subscription:
        query &= Q(
            **{
                f"{prefix}payment_profile__peer_subscription__subscription"
                "__stripe_data__status__in": [
                    SubscriptionStatus.active,
                    SubscriptionStatus.trialing,
                ],
            },
        )
        # A paused plan keeps its ``active`` status, so exclude it explicitly.
        query &= Q(
            **{
                f"{prefix}payment_profile__peer_subscription__paused_at__isnull": True,
            },
        )
    if requirements.require_verification_to_publish:
        query &= Q(**{f"{prefix}peer_profile__is_verified": True})
    return query


def _has_paid_participants(meeting) -> bool:
    """Whether *meeting* has at least one paid participant."""
    from neuromancers_network.meetings.models import Booking  # noqa: PLC0415
    from neuromancers_network.meetings.models import BookingStatus  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequestStatus  # noqa: PLC0415

    return (
        MeetingRequest.objects.filter(
            meeting=meeting,
            status=MeetingRequestStatus.PAID,
        ).exists()
        or Booking.objects.filter(meeting=meeting, status=BookingStatus.PAID).exists()
    )


def enforce_subscription_lapse(payment_profile) -> None:
    """Unpublish meetings that cannot remain live after a subscription lapses.

    1:1 meetings are always unpublished. Group meetings are unpublished only
    when they have no paid participants; a group with paid participants stays
    published but drops out of feeds and cannot take new bookings (the
    eligibility gate and feed filter handle those).
    """
    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingStatus  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingType  # noqa: PLC0415

    user = payment_profile.user
    published = Meeting.objects.filter(peer=user, status=MeetingStatus.PUBLISHED)
    for meeting in published:
        keep_published = (
            meeting.meeting_type == MeetingType.GROUP
            and _has_paid_participants(meeting)
        )
        if keep_published:
            continue
        meeting.unpublish()
        meeting.save(validate=False, update_fields=["status", "updated_at"])


def _add_months(value: datetime, months: int) -> datetime:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def window_occurrences(
    window: PeerAvailability,
    now: datetime,
    horizon: datetime,
) -> Iterator[tuple[datetime, datetime]]:
    """Expand *window* into concrete ``(start, end)`` occurrences."""
    base_start = window.start
    base_end = window.end
    if not window.occurrence or window.occurrence not in AvailabilityOccurrence.values:
        yield base_start, base_end
        return

    occurrence_start = window.occurrence_starts_at or now
    occurrence_end = window.occurrence_ends_at or _add_months(occurrence_start, 12)
    step = {
        AvailabilityOccurrence.DAILY: timedelta(days=1),
        AvailabilityOccurrence.WEEKLY: timedelta(weeks=1),
        AvailabilityOccurrence.MONTHLY: None,
    }[window.occurrence]

    current = occurrence_start
    count = 0
    while current <= occurrence_end:
        start = current.replace(
            hour=base_start.hour,
            minute=base_start.minute,
            second=base_start.second,
            microsecond=base_start.microsecond,
        )
        if start > horizon:
            return
        end = current.replace(
            hour=base_end.hour,
            minute=base_end.minute,
            second=base_end.second,
            microsecond=base_end.microsecond,
        )
        if end <= start:
            end += timedelta(days=1)
        yield start, end
        count += 1
        if count >= MAX_RECURRENCE_OCCURRENCES:
            logger.warning(
                "Stopped expanding availability window %s after %s occurrences",
                window.pk,
                MAX_RECURRENCE_OCCURRENCES,
            )
            return
        current = _add_months(current, 1) if step is None else current + step


def _subtract_interval(
    interval: tuple[datetime, datetime],
    booked: tuple[datetime, datetime],
) -> list[tuple[datetime, datetime]]:
    """Return the parts of *interval* not covered by *booked*."""
    start, end = interval
    booked_start, booked_end = booked
    if end <= booked_start or start >= booked_end:
        return [interval]
    remaining = []
    if booked_start > start:
        remaining.append((start, booked_start))
    if booked_end < end:
        remaining.append((booked_end, end))
    return remaining


def _subtract_bookings(
    start: datetime,
    end: datetime,
    booked: Iterable[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    pieces = [(start, end)]
    for booked_range in booked:
        pieces = [
            piece
            for current in pieces
            for piece in _subtract_interval(current, booked_range)
        ]
        if not pieces:
            break
    return pieces


def _booked_ranges(
    user: UserType,
    exclude_request=None,
) -> Iterator[tuple[datetime, datetime]]:
    from neuromancers_network.meetings.models import MeetingRequest  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingRequestStatus  # noqa: PLC0415
    from neuromancers_network.meetings.models import MeetingType  # noqa: PLC0415

    queryset = MeetingRequest.objects.filter(
        meeting__peer=user,
        meeting__meeting_type=MeetingType.ONE_ON_ONE,
        status__in=[MeetingRequestStatus.APPROVED, MeetingRequestStatus.PAID],
        requested_start_time__isnull=False,
        requested_duration_minutes__isnull=False,
    )
    if exclude_request is not None and exclude_request.pk:
        queryset = queryset.exclude(pk=exclude_request.pk)
    for request in queryset:
        start = request.requested_start_time
        if not start or not request.requested_duration_minutes:
            continue
        end = start + timedelta(minutes=request.requested_duration_minutes)
        yield start, end


def available_slots(
    user: UserType,
    *,
    horizon_days: int = 90,
    until: datetime | None = None,
    exclude_request=None,
) -> list[tuple[datetime, datetime]]:
    """Return the *user*'s available 1:1 slots, excluding booked time.

    Each availability window is expanded (one-off or recurring) and any time
    already booked by an approved/paid request is removed. Pass *until* to
    extend the horizon to a specific moment (used when validating a request).
    """
    now = timezone.now()
    horizon = until or now + timedelta(days=horizon_days)
    booked = list(_booked_ranges(user, exclude_request))

    slots: list[tuple[datetime, datetime]] = []
    for window in PeerAvailability.objects.filter(peer=user):
        for start, end in window_occurrences(window, now, horizon):
            slots.extend(_subtract_bookings(start, end, booked))
    return [(start, end) for start, end in slots if end > now]
