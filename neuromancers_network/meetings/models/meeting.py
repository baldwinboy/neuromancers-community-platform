from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import transition
from taggit.managers import TaggableManager

from neuromancers_network.core.models.base import Timestamped

from .choices import ApprovalPolicy
from .choices import MeetingRequestStatus
from .choices import MeetingStatus
from .choices import MeetingType
from .choices import PricingType

MIN_DURATION_MINUTES = 5
MAX_DURATION_MINUTES = 120
MAX_GROUP_CAPACITY = 200
GROUP_MINIMUM_START_AHEAD_MINUTES = 30
ROOM_WINDOW_EXPIRED_MINUTES = 20
FORCE_REGENERATE_GRACE_MINUTES = 10

VALID_MEETING_LINK_DOMAINS = {
    "whereby.com",
    "google.com",
    "microsoft.com",
    "zoom.us",
    "proton.me",
    "jit.si",
    "gotomeeting.com",
    "zoho.meet",
    "livestorm.co",
    "webex.com",
    "uberconference.com",
}


def _is_valid_meeting_link(url):
    """Return True if *url* belongs to a known video-meeting platform."""
    if not url:
        return False
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    host = host.lower()
    return any(host == d or host.endswith("." + d) for d in VALID_MEETING_LINK_DOMAINS)


class Meeting(Timestamped):
    peer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meetings",
    )
    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"))
    terms = models.TextField(
        _("Terms"),
        blank=True,
        help_text=_("Free-text terms and conditions."),
    )
    meeting_type = models.CharField(
        _("Meeting type"),
        max_length=10,
        choices=MeetingType.choices,
    )
    meeting_link = models.URLField(
        _("Meeting link"),
        blank=True,
        help_text=_(
            "Auto-populated with a Whereby meeting link close to the time "
            "of the event if left empty. Only valid for group meetings.",
        ),
    )
    whereby_meeting_id = models.CharField(
        _("Whereby meeting ID"),
        max_length=255,
        blank=True,
    )
    pricing_type = models.CharField(
        _("Pricing type"),
        max_length=20,
        choices=PricingType.choices,
    )
    price = models.DecimalField(
        _("Price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    sliding_scale_min = models.DecimalField(
        _("Sliding scale min"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    sliding_scale_max = models.DecimalField(
        _("Sliding scale max"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(_("Currency"), max_length=3, default="GBP")
    approval_policy = models.CharField(
        _("Approval policy"),
        max_length=20,
        choices=ApprovalPolicy.choices,
    )
    refund_requires_approval = models.BooleanField(
        _("Refund requires approval"),
        default=True,
    )
    max_participants = models.PositiveIntegerField(
        _("Max participants"),
        null=True,
        blank=True,
        validators=[MaxValueValidator(MAX_GROUP_CAPACITY)],
        help_text=_(
            "Maximum number of participants. Required for group meetings, up to 200.",
        ),
    )
    languages = models.ManyToManyField(
        "taxonomy.Language",
        blank=True,
        related_name="meetings",
    )
    tags = TaggableManager(blank=True)
    status = FSMField(
        _("Status"),
        default=MeetingStatus.DRAFT,
        choices=MeetingStatus.choices,
    )

    # Scheduling — required for group meetings, optional for 1:1
    scheduled_at = models.DateTimeField(_("Scheduled at"), null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(
        _("Duration (minutes)"),
        null=True,
        blank=True,
        validators=[
            MinValueValidator(MIN_DURATION_MINUTES),
            MaxValueValidator(MAX_DURATION_MINUTES),
        ],
    )

    # Recurrence — only applicable to group meetings
    recurrence_rule = models.ForeignKey(
        "meetings.RecurrenceRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meetings",
        help_text=_(
            "Recurrence rule for group meetings. Not applicable to 1:1 meetings.",
        ),
    )

    class Meta:
        ordering = ["-scheduled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["peer", "title"],
                condition=models.Q(status=MeetingStatus.PUBLISHED),
                name="%(app_label)s_%(class)s_unique_published_title_per_peer",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "scheduled_at"],
                name="meeting_status_sched_idx",
            ),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        validate = kwargs.pop("validate", True)
        if validate:
            self.full_clean()
        super().save(*args, **kwargs)

    @property
    def requires_approval(self) -> bool:
        return self.approval_policy == ApprovalPolicy.APPROVAL_REQUIRED

    @property
    def requires_payment_before_join(self) -> bool:
        return self.approval_policy == ApprovalPolicy.PAY_BEFORE_JOIN

    @property
    def allows_payment_after_join(self) -> bool:
        return self.approval_policy == ApprovalPolicy.PAY_AFTER_JOIN

    @property
    def initial_request_status(self) -> str:
        if self.requires_approval:
            return MeetingRequestStatus.PENDING_APPROVAL
        if self.requires_payment_before_join:
            return MeetingRequestStatus.PENDING_PAYMENT
        return MeetingRequestStatus.APPROVED

    @transition(
        field=status,
        source=MeetingStatus.DRAFT,
        target=MeetingStatus.PUBLISHED,
    )
    def publish(self):
        pass

    @transition(
        field=status,
        source=MeetingStatus.PUBLISHED,
        target=MeetingStatus.DRAFT,
    )
    def unpublish(self):
        pass

    @transition(
        field=status,
        source=[MeetingStatus.DRAFT, MeetingStatus.PUBLISHED],
        target=MeetingStatus.ARCHIVED,
    )
    def archive(self):
        pass

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError  # noqa: PLC0415

        errors = {}

        if self.meeting_type == MeetingType.GROUP:
            if not self.scheduled_at:
                errors["scheduled_at"] = _("Group meetings must have a start time.")
            if not self.duration_minutes:
                errors["duration_minutes"] = _("Group meetings must have a duration.")
            if self.scheduled_at and self.scheduled_at < timezone.now() + timedelta(
                minutes=GROUP_MINIMUM_START_AHEAD_MINUTES,
            ):
                errors["scheduled_at"] = _(
                    "Group meetings must start at least 30 minutes in the future.",
                )

        if self.meeting_type == MeetingType.ONE_ON_ONE and self.recurrence_rule_id:
            errors["recurrence_rule"] = _(
                "Recurrence is not supported for 1:1 meetings.",
            )

        if (
            self.meeting_type == MeetingType.ONE_ON_ONE
            and self.max_participants is not None
        ):
            errors["max_participants"] = _(
                "Max participants is not applicable to 1:1 meetings.",
            )

        if (
            self.max_participants is not None
            and self.max_participants > MAX_GROUP_CAPACITY
        ):
            errors["max_participants"] = (
                _(
                    "Max participants cannot exceed %s.",
                )
                % MAX_GROUP_CAPACITY
            )

        if errors:
            raise ValidationError(errors)

    def populate_meeting_link(self, *, force=False):
        """
        Create a Whereby room and populate meeting_link + whereby_meeting_id.

        Parameters
        ----------
        force : bool
            When *True*, regenerate the link even if a valid one already
            exists, provided the meeting is in the future or ≤ 20 minutes
            in the past.

        Guards
        ------
        - Always skipped for non-group meetings or when required fields are
          missing.
        - Always skipped when scheduled_at is more than 20 minutes in the
          past (room window has expired).
        - When *force=False* (default), also skipped when scheduled_at is
          more than 10 minutes in the past, or a valid meeting-link URL
          already exists.
        """
        from whereby.client import meetings as whereby_meetings  # noqa: PLC0415
        from whereby.schemas import MeetingsApplicationJson  # noqa: PLC0415

        if (
            not self.scheduled_at
            or not self.duration_minutes
            or self.meeting_type != MeetingType.GROUP
        ):
            return

        now = timezone.now()
        minutes_in_past = (now - self.scheduled_at).total_seconds() / 60

        if minutes_in_past > ROOM_WINDOW_EXPIRED_MINUTES:
            return

        if not force and minutes_in_past > FORCE_REGENERATE_GRACE_MINUTES:
            return

        if not force and _is_valid_meeting_link(self.meeting_link):
            return

        end_date = self.scheduled_at + timedelta(minutes=self.duration_minutes)
        data = MeetingsApplicationJson(
            end_date=end_date.isoformat(),
            start_date=self.scheduled_at.isoformat(),
        )
        result = whereby_meetings(data=data)
        self.meeting_link = result.room_url
        self.whereby_meeting_id = result.meeting_id
        self.save(validate=False, update_fields=["meeting_link", "whereby_meeting_id"])

    @property
    def is_fully_booked(self):
        if self.meeting_type != MeetingType.GROUP or self.max_participants is None:
            return False
        return self.requests.count() >= self.max_participants

    def available_spots(self):
        if self.meeting_type != MeetingType.GROUP or self.max_participants is None:
            return None
        return max(0, self.max_participants - self.requests.count())
