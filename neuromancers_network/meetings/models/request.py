from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import transition

from neuromancers_network.core.models.base import Timestamped

from .choices import MeetingRequestStatus
from .meeting import MAX_DURATION_MINUTES
from .meeting import MIN_DURATION_MINUTES
from .meeting import Meeting


class MeetingRequest(Timestamped):
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    support_seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meeting_requests",
    )
    status = FSMField(
        _("Status"),
        default=MeetingRequestStatus.PENDING_APPROVAL,
        choices=MeetingRequestStatus.choices,
        protected=True,
    )
    price_paid = models.DecimalField(
        _("Price paid"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    seeker_terms = models.TextField(
        _("Support seeker terms / needs"),
        blank=True,
    )
    peer_terms = models.TextField(
        _("Peer terms of engagement"),
        blank=True,
    )
    stripe_payment_intent_id = models.CharField(
        _("Stripe payment intent ID"),
        max_length=255,
        blank=True,
    )

    # Seeker-requested scheduling — only for 1:1 meetings
    requested_start_time = models.DateTimeField(
        _("Requested start time"),
        null=True,
        blank=True,
        help_text=_(
            "The start time requested by the support seeker for a 1:1 meeting.",
        ),
    )
    requested_duration_minutes = models.PositiveIntegerField(
        _("Requested duration (minutes)"),
        null=True,
        blank=True,
        validators=[
            MinValueValidator(MIN_DURATION_MINUTES),
            MaxValueValidator(MAX_DURATION_MINUTES),
        ],
        help_text=_("The duration requested by the support seeker (5-120 minutes)."),
    )

    # Meeting link — auto-populated via whereby if left empty (1:1 meetings only)
    meeting_link = models.URLField(
        _("Meeting link"),
        blank=True,
        help_text=_(
            "Auto-populated with a Whereby meeting link close to the time "
            "of the event if left empty. Only valid for 1:1 meetings.",
        ),
    )
    whereby_meeting_id = models.CharField(
        _("Whereby meeting ID"),
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["meeting", "support_seeker"],
                name="%(app_label)s_%(class)s_unique_meeting_per_seeker",
            ),
        ]

    def __str__(self):
        return f"Request for {self.meeting} by {self.support_seeker}"

    @transition(
        field=status,
        source=MeetingRequestStatus.PENDING_APPROVAL,
        target=MeetingRequestStatus.APPROVED,
    )
    def approve(self):
        pass

    @transition(
        field=status,
        source=MeetingRequestStatus.PENDING_APPROVAL,
        target=MeetingRequestStatus.REJECTED,
    )
    def reject(self):
        pass

    @transition(
        field=status,
        source=[MeetingRequestStatus.APPROVED, MeetingRequestStatus.PENDING_APPROVAL],
        target=MeetingRequestStatus.PAID,
    )
    def mark_paid(self):
        pass

    @transition(
        field=status,
        source=MeetingRequestStatus.PAID,
        target=MeetingRequestStatus.COMPLETED,
    )
    def complete(self):
        pass

    @transition(
        field=status,
        source=[
            MeetingRequestStatus.PENDING_APPROVAL,
            MeetingRequestStatus.APPROVED,
            MeetingRequestStatus.PAID,
        ],
        target=MeetingRequestStatus.CANCELLED,
    )
    def cancel(self):
        pass

    def populate_meeting_link(self):
        """
        Create a Whereby room and populate meeting_link + whereby_meeting_id.
        Called by Celery task close to meeting time, or manually.
        Only applicable to 1:1 meetings.
        """
        from whereby.client import meetings as whereby_meetings  # noqa: PLC0415
        from whereby.schemas import MeetingsApplicationJson  # noqa: PLC0415

        start = self.requested_start_time
        duration = self.requested_duration_minutes
        if not start or not duration or self.meeting_link:
            return

        end_date = start + timedelta(minutes=duration)
        data = MeetingsApplicationJson(
            end_date=end_date.isoformat(),
            start_date=start.isoformat(),
        )
        result = whereby_meetings(data=data)
        self.meeting_link = result.room_url
        self.whereby_meeting_id = result.meeting_id
        self.save(update_fields=["meeting_link", "whereby_meeting_id"])
