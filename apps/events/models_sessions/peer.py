import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import int_list_validator
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext as _

from .abstract import (
    AbstractSession,
    AbstractSessionAvailability,
    AbstractSessionRequest,
    AbstractSessionRequestStatusChoices,
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
        validators=[int_list_validator(sep=",", message=(_("Only digits allowed")))],
    )
    per_hour_price = models.PositiveSmallIntegerField(
        help_text=_(
            "Support seekers will be charged this price based on the duration of their requested session if set"
        ),
        null=True,
    )
    concessionary_per_hour_price = models.PositiveSmallIntegerField(
        help_text=_(
            "Support seekers will be charged this price based on the duration of their requested session if set and if they are allowed to pay a reduced price"
        ),
        null=True,
    )
    is_published = models.BooleanField(default=False, unique_for_date="starts_at")
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
                condition=Q(access_before_payment=True) & Q(price=0),
                name="peer_access_before_payment_price_zero",
                violation_error_message=_(
                    "Free sessions can't require access before payment"
                ),
            ),
        ]


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
            )
        ]

    def __str__(self):
        return (
            f"{self.session.title}: {self.occurrence} from {self.starts_at} to {self.ends_at} {self.occurrence}"
            if self.occurrence
            else f"{self.session.title}: from {self.starts_at} to {self.ends_at} {self.occurrence}"
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
                violation_error_message=_("Group session must last at least 5 minutes"),
            ),
        ]

    def __str__(self):
        return f"{self.session.title} for {self.attendee.username} from {self.starts_at} to {self.ends_at}"

    def validate_unique(self, *args, **kwargs):
        """
        Session requests should not overlap with existing approved session requests from the same attendee
        """
        overlapping_requests = PeerSessionRequest.objects.filter(
            Q(starts_at__lt=self.ends_at, ends_at__gt=self.starts_at)
            | Q(starts_at__gte=self.starts_at, ends_at__lte=self.ends_at),
            attendee=self.attendee,
            session=self.session,
            status=AbstractSessionRequestStatusChoices.APPROVED,
        )

        if overlapping_requests.exists():
            raise ValidationError(
                _(
                    "Session requests should not conflict with existing session requests from the same attendee"
                )
            )

        super(PeerSessionRequest, self).validate_unique(*args, **kwargs)


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
