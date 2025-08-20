import uuid
from datetime import timedelta, datetime

from dateutil.relativedelta import relativedelta
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext as _
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from apps.events.choices import (
    SessionAvailabilityOccurrenceChoices,
    SessionRequestStatusChoices,
    filtered_currencies
)
from apps.events.utils import subtract_event

from .abstract import (
    AbstractSession,
    AbstractSessionAvailability,
    AbstractSessionRequest,
    User,
)


class PeerSession(AbstractSession):
    """
    Peer sessions may be rquested and attended by a single `SupportSeeker` user for a selected duration of time.
    """

    durations = models.CharField(
        help_text=_(
            "These are durations (in minutes) that a session may be booked for"
        ),
        max_length=320,
    )
    per_hour_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
        help_text=_(
            "Support seekers will be charged this price based on the duration of their requested session if set"
        ),
        null=True,
        blank=True,
    )
    concessionary_per_hour_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0, message=_("Cannot charge negative values"))],
        help_text=_(
            "Support seekers will be charged this price based on the duration of their requested session if set and if they are allowed to pay a reduced price"
        ),
        null=True,
        blank=True,
    )
    is_published = models.BooleanField(default=False)
    host = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="peer_sessions"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["host", "title", "is_published"],
                name="unique_published_peer_session",
            ),
            models.CheckConstraint(
                # If the session is free, access before payment can't be withheld
                condition=Q(price__gt=0) | Q(access_before_payment=True),
                name="peer_access_before_payment_price_zero",
                violation_error_message=_(
                    "Free sessions can't require access before payment"
                ),
            ),
        ]

        permissions = [
            ("request_session", "Request session"),
            ("manage_availability", "Manage Availability"),
            ("schedule_session", "Schedule session"),
        ]

    @property
    def currency_symbol(self):
        _currency = filtered_currencies.get(self.currency, None)

        if not _currency:
            return ""
        
        return _currency.get("symbol", None)

    @property
    def available_slots(self) -> list[tuple[datetime, datetime]]:
        """
        Returns a list of tuples with the availability start date and end date. Excludes booked sessions.
        """
        slots = []
        now = datetime.now()

        future_approved_requests = self.requests.filter(
            status=SessionRequestStatusChoices.APPROVED, starts_at__gte=now
        ).values_list("starts_at", "ends_at")

        # Convert to list of tuples for exclusion
        booked_ranges = [(start, end) for start, end in future_approved_requests]

        for availability in self.availability.all():
            base_start = availability.starts_at
            base_end = availability.ends_at

            if not base_start or not base_end:
                continue

            if availability.occurrence is not None:
                occurrence_start = availability.occurrence_starts_at or now
                occurrence_end = availability.occurrence_ends_at or (
                    occurrence_start + relativedelta(years=1)
                )

                delta = {
                    SessionAvailabilityOccurrenceChoices.DAILY: timedelta(days=1),
                    SessionAvailabilityOccurrenceChoices.WEEKLY: timedelta(weeks=1),
                    SessionAvailabilityOccurrenceChoices.MONTHLY: relativedelta(
                        months=1
                    ),
                }.get(availability.occurrence)

                current = occurrence_start

                while current <= occurrence_end:
                    start_dt = current.replace(
                        hour=base_start.hour,
                        minute=base_start.minute,
                        second=base_start.second,
                        microsecond=base_start.microsecond,
                    )
                    end_dt = current.replace(
                        hour=base_end.hour,
                        minute=base_end.minute,
                        second=base_end.second,
                        microsecond=base_end.microsecond,
                    )

                    # If end is before start (e.g., overnight availability), adjust end
                    if end_dt <= start_dt:
                        end_dt += timedelta(days=1)

                    # Exclude booked times
                    non_overlapping_slots = []
                    for booked_start, booked_end in booked_ranges:
                        if (start_dt <= booked_end and end_dt >= booked_start):
                           non_overlapping_slots += subtract_event((start_dt, end_dt), (booked_start, booked_end))

                    if non_overlapping_slots:
                        slots += non_overlapping_slots
                    else:
                        slots.append((start_dt, end_dt))
                    
                    if delta:
                        current += delta

            else:
                # One-off availability
                non_overlapping_slots = []
                for booked_start, booked_end in booked_ranges:
                    if (base_start <= booked_end and base_end >= booked_start):
                        non_overlapping_slots += subtract_event((base_start, base_end), (booked_start, booked_end))

                if non_overlapping_slots:
                    slots += non_overlapping_slots
                else:
                    slots.append((base_start, base_end))

        return slots

class PeerSessionUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(PeerSession, on_delete=models.CASCADE)


class PeerSessionGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(PeerSession, on_delete=models.CASCADE)


class PeerSessionAvailability(AbstractSessionAvailability):
    """
    Peer sessions may be requested to be scheduled at these times
    """

    session = models.ForeignKey(
        PeerSession, on_delete=models.CASCADE, related_name="availability"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "starts_at", "occurrence_starts_at"],
                name="unique_peer_session_availability",
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gte=(F("starts_at") + timedelta(minutes=5)))
                & Q(ends_at__lte=(F("starts_at") + timedelta(days=1))),
                name="availability_ends_at_gte_starts_at",
                violation_error_message=_(
                    "Availabilty must last between 5 minutes and 1 day"
                ),
            ),
            models.CheckConstraint(
                condition=Q(occurrence_starts_at__isnull=True)
                | Q(occurrence_ends_at__isnull=True)
                | Q(
                    occurrence_ends_at__gte=(
                        F("occurrence_starts_at") + timedelta(days=2)
                    )
                ),
                name="availability_occurrence_ends_at_gte_starts_at",
                violation_error_message=_(
                    "Availabilty occurrence must last at least two days. If you want an availability that does not recur, don't set any occurrence."
                ),
            ),
        ]

    def __str__(self):
        if self.occurrence is None:
            starts_at_formatted = self.starts_at.strftime("%A, %d %B %Y, %H:%M")
            ends_at_formatted = self.ends_at.strftime("%A, %d %B %Y, %H:%M")
            return f"From {starts_at_formatted} to {ends_at_formatted}"

        starts_at_formatted = self.starts_at.strftime("%H:%M")
        ends_at_formatted = self.ends_at.strftime("%H:%M")

        if self.occurrence_starts_at:
            occurrence_starts_at_formatted = self.occurrence_starts_at.strftime(
                "%A, %d %B %Y, %H:%M"
            )

        if self.occurrence_ends_at:
            occurrence_ends_at_formatted = self.occurrence_ends_at.strftime(
                "%A, %d %B %Y, %H:%M"
            )

        if occurrence_starts_at_formatted and occurrence_ends_at_formatted:
            return f"{self.get_occurrence_display()} from {starts_at_formatted} to {ends_at_formatted} between {occurrence_starts_at_formatted} and {occurrence_ends_at_formatted}"

        if occurrence_starts_at_formatted:
            return f"{self.get_occurrence_display()} from {starts_at_formatted} to {ends_at_formatted} after {occurrence_starts_at_formatted}"
        if occurrence_ends_at_formatted:
            return f"{self.get_occurrence_display()} from {starts_at_formatted} to {ends_at_formatted} until {occurrence_ends_at_formatted}"

        return f"{self.get_occurrence_display()} from {starts_at_formatted} to {ends_at_formatted}"


class PeerSessionAvailabilityUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(
        PeerSessionAvailability, on_delete=models.CASCADE
    )


class PeerSessionAvailabilityGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(
        PeerSessionAvailability, on_delete=models.CASCADE
    )


class PeerSessionRequest(AbstractSessionRequest):
    """
    Peer session requests may be sent from `SupportSeeker` users to `Peer` users
    """

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    attendee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="peer_session_requests"
    )
    session = models.ForeignKey(
        PeerSession, on_delete=models.CASCADE, related_name="requests"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attendee", "session", "starts_at"],
                name="unique_peer_session_request",
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gte=(F("starts_at") + timedelta(minutes=5))),
                name="peer_ends_at_gte_starts_at",
                violation_error_message=_("Peer session must last at least 5 minutes"),
            ),
        ]

        permissions = [
            ("approve_peer_request", "Approve peer request"),
        ]

    def __str__(self):
        return f"{self.session.title} for {self.attendee.username} from {self.starts_at} to {self.ends_at}"
    
    @property
    def price(self):
        _price = self.session.price or 0
        duration_hrs = (self.ends_at - self.starts_at).total_seconds() / 3600

        if self.pay_concessionary_price:
            if self.session.concessionary_per_hour_price:
                return duration_hrs * self.session.concessionary_per_hour_price
            
            return self.session.concessionary_price or 0
        
        if self.session.per_hour_price:
            return duration_hrs * self.session.per_hour_price
    
        return _price

class PeerSessionRequestUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(PeerSessionRequest, on_delete=models.CASCADE)


class PeerSessionRequestGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(PeerSessionRequest, on_delete=models.CASCADE)


class PeerScheduledSession(models.Model):
    """
    Peer scheduled sessions may be created after requests are sent and approved
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting_link = models.URLField(
        help_text="This will be automatically generated if not set", null=True
    )
    request = models.OneToOneField(
        PeerSessionRequest,
        on_delete=models.CASCADE,
        related_name="scheduled_session",
    )

    def __str__(self):
        return str(self.request)


class PeerScheduledSessionUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(PeerScheduledSession, on_delete=models.CASCADE)


class PeerScheduledSessionGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(PeerScheduledSession, on_delete=models.CASCADE)
