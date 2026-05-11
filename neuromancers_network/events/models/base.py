import contextlib

from auditlog.registry import auditlog
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField
from django_fsm import TransitionNotAllowed
from django_fsm import transition
from djstripe.fields import StripeCurrencyCodeField
from slugify import slugify
from wagtail.fields import RichTextField

from neuromancers_network.common.models.base import TimestampedModel
from neuromancers_network.common.models.base import UUIDModel


class SessionBookingQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.is_staff:
            return self
        return self.filter(
            models.Q(attendee=user) | models.Q(host=user),
        )

    def accessible(self, user, session):
        if user.is_staff:
            return self.filter(session=session)
        return self.filter(
            models.Q(session=session) & (models.Q(attendee=user) | models.Q(host=user)),
        )


class SessionManager(models.Manager):
    def published(self):
        return self.filter(is_published=True)

    def visible_for(self, user):
        if user.is_staff:
            return self.all()
        return self.filter(
            models.Q(is_published=True) | models.Q(host=user),
        )


class SessionType(models.TextChoices):
    PEER = "peer", _("Peer")
    GROUP = "group", _("Group")


class VisibilityType(models.TextChoices):
    PUBLIC = "public", _("PUBLIC")
    PRIVATE = "private", _("PRIVATE")


class SessionPriceType(models.TextChoices):
    FIXED = "fixed", _("Fixed")
    HOURLY_RATE = "hourly_rate", _("Hourly rate")
    SLIDING_SCALE = "sliding_scale", _("Sliding scale")


class BookingStatus(models.TextChoices):
    PENDING_APPROVAL = "pending_approval", _("Pending approval")
    APPROVED = "approved", _("Approved")
    CONFIRMED = "confirmed", _("Confirmed")
    CANCELLED = "cancelled", _("Cancelled")
    COMPLETED = "completed", _("Completed")
    EXPIRED = "expired", _("Expired")


class PaymentStatus(models.TextChoices):
    NOT_REQUIRED = "not_required", _("Not required")
    REQUIRED = "required", _("Required")
    CHECKOUT_CREATED = "checkout_created", _("Checkout created")
    PROCESSING = "processing", _("Processing")
    PAID = "paid", _("Paid")
    FAILED = "failed", _("Failed")
    EXPIRED = "expired", _("Expired")
    REFUNDED = "refunded", _("Refunded")
    REFUND_PENDING_APPROVAL = (
        "refund_pending_approval",
        _("Refund pending approval"),
    )


MIN_SLIDING_SCALE_PRICE_POINTS = 2


def validate_price_rows(price_rows):
    grouped_prices = {
        SessionPriceType.FIXED: [],
        SessionPriceType.HOURLY_RATE: [],
        SessionPriceType.SLIDING_SCALE: [],
    }

    for row in price_rows:
        grouped_prices[row.price_type].append(row.amount_subunit)

    missing_types = [
        price_type for price_type, prices in grouped_prices.items() if not prices
    ]
    if missing_types:
        raise ValidationError(
            _("Missing pricing configuration for: %(types)s")
            % {"types": ", ".join(sorted(missing_types))},
        )

    if len(grouped_prices[SessionPriceType.FIXED]) != 1:
        raise ValidationError(
            _("Fixed pricing must contain exactly 1 value."),
        )
    if len(grouped_prices[SessionPriceType.HOURLY_RATE]) != 1:
        raise ValidationError(
            _("Hourly pricing must contain exactly 1 value."),
        )

    sliding_scale_prices = grouped_prices[SessionPriceType.SLIDING_SCALE]
    if len(sliding_scale_prices) < MIN_SLIDING_SCALE_PRICE_POINTS:
        raise ValidationError(
            _("Sliding scale must include at least 2 values."),
        )
    if sliding_scale_prices != sorted(sliding_scale_prices):
        raise ValidationError(
            _("Sliding scale values must be sorted in ascending order."),
        )
    if len(set(sliding_scale_prices)) != len(sliding_scale_prices):
        raise ValidationError(
            _("Sliding scale values must be unique."),
        )


class SessionSeries(UUIDModel):
    """SessionSeries — user-created grouping for sessions."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_series",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "events"
        verbose_name_plural = _("Series of sessions")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @staticmethod
    def get_form_fields():
        return ["name", "description", "is_active"]


class Session(TimestampedModel, UUIDModel):
    """
    - 1:1 sessions with per-duration pricing and booking
    - GroupSession — fixed-time group sessions with capacity.
    """

    session_type = models.CharField(
        max_length=16,
        choices=SessionType.choices,
    )

    title = models.CharField(max_length=255)
    description = RichTextField(blank=True)
    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "If this is NOT a group session, then bookings may be requested to start any time after this.",
        ),
    )
    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "If this is NOT a group session, then bookings may be requested to end any time before this.",
        ),
    )
    languages = models.JSONField(default=list, blank=True)
    currency = StripeCurrencyCodeField(default="gbp")
    visibility = models.CharField(
        max_length=8,
        choices=VisibilityType.choices,
        default=VisibilityType.PUBLIC,
        help_text=_(
            "If visibility is set to private, then users will only be able to see the session using a direct link",
        ),
    )
    is_published = models.BooleanField(default=False)
    capacity = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(200),
        ],
        help_text=_(
            "The number of people who may join the session (excluding the host). If this is NOT a group session, the number of people who can join is always 1.",
        ),
    )
    min_duration_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=30,
        help_text=_("Minimum booking duration in minutes (peer sessions)"),
    )
    max_duration_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=120,
        help_text=_("Maximum booking duration in minutes (peer sessions)"),
    )
    tos_text = models.TextField(blank=True)
    intake_form_schema = models.JSONField(null=True, blank=True)
    require_approval = models.BooleanField(
        default=True,
        help_text=_(
            """
            If enabled, approval is required before a booking is confirmed.
            """,
        ),
    )
    require_refund_approval = models.BooleanField(
        default=False,
        help_text=_(
            """
            If enabled, approval is required before a refund is confirmed.
            """,
        ),
    )
    require_payment_before_joining = models.BooleanField(
        default=True,
        help_text=_(
            """
            If enabled, attendees must complete payment
            before they can join the session.
            """,
        ),
    )
    meeting_link = models.URLField(
        blank=True,
        help_text=_(
            "This will be automatically generated if left blank. If this is NOT a group session, ensure that only you and your attendee have access to the link",
        ),
    )
    category = models.ForeignKey(
        "SessionSeries",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_sessions",
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)s_sessions",
    )

    objects = SessionManager()

    class Meta:
        indexes = [
            models.Index(fields=["host", "is_published"]),
            models.Index(fields=["is_published", "visibility"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.session_type == SessionType.PEER and not self.capacity:
            self.capacity = 1
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.is_published:
            if not self.pk:
                raise ValidationError(
                    _("Session must be saved before publishing pricing."),
                )
            validate_price_rows(self.price_options.all())
            has_paid_options = self.price_options.filter(
                amount_subunit__gt=0,
            ).exists()
            if has_paid_options and not self.host.stripe_account:
                raise ValidationError(
                    _(
                        "Host must connect a Stripe account before publishing paid sessions.",
                    ),
                )
        if self.min_duration_minutes and self.max_duration_minutes:
            if self.min_duration_minutes > self.max_duration_minutes:
                raise ValidationError(
                    _("Minimum duration cannot exceed maximum duration."),
                )

    def get_prices(self, price_type):
        return list(
            self.price_options.filter(price_type=price_type)
            .order_by("sort_order")
            .values_list("amount_subunit", flat=True),
        )

    @property
    def is_group(self):
        return self.session_type == SessionType.GROUP

    @property
    def is_peer(self):
        return self.session_type == SessionType.PEER

    @property
    def spots_remaining(self):
        if self.session_type != SessionType.GROUP:
            return None
        return (
            self.capacity
            - self.bookings.filter(
                booking_status=BookingStatus.CONFIRMED,
            ).count()
        )

    @staticmethod
    def get_form_fields():
        return [
            "title",
            "description",
            "languages",
            "visibility",
            "is_published",
            "category",
            "tos_text",
            "intake_form_schema",
            "require_approval",
            "require_refund_approval",
            "require_payment_before_joining",
        ]


class Review(TimestampedModel, UUIDModel):
    """
    A review for a session.
    """

    session = models.ForeignKey(
        "Session",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text=_("1-5 stars"),
    )
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = [("session", "reviewer")]

    def __str__(self):
        return self.comment

    @staticmethod
    def get_form_fields():
        return ["rating", "comment"]


class DurationPrice(models.Model):
    session = models.ForeignKey(
        "Session",
        on_delete=models.CASCADE,
        related_name="duration_prices",
    )
    duration_minutes = models.PositiveSmallIntegerField(
        help_text=_("Duration in minutes"),
    )
    amount_cents = models.PositiveIntegerField(
        help_text=_("Price in cents"),
    )

    class Meta:
        unique_together = [("session", "duration_minutes")]

    def __str__(self):
        return f"{self.duration_minutes}min @ {self.amount_cents}c"


class SessionPrice(models.Model):
    session = models.ForeignKey(
        "Session",
        on_delete=models.CASCADE,
        related_name="price_options",
    )
    price_type = models.CharField(
        max_length=20,
        choices=SessionPriceType.choices,
    )
    amount_subunit = models.PositiveIntegerField(help_text=_("Price in subunits"))
    min_amount_subunit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Minimum price for sliding scale (in subunits)"),
    )
    max_amount_subunit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum price for sliding scale (in subunits)"),
    )
    currency = StripeCurrencyCodeField(default="gbp")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["price_type", "sort_order", "amount_subunit"]
        unique_together = ["session", "price_type", "sort_order"]

    def __str__(self):
        return f"{self.session.title} | {self.price_type} {self.amount_subunit}"


class WebhookEventLog(models.Model):
    """Tracks processed webhook events for idempotent processing."""

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=128)
    processed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, default="processed")

    class Meta:
        verbose_name = _("Webhook Event Log")
        verbose_name_plural = _("Webhook Event Logs")
        ordering = ["-processed_at"]

    def __str__(self):
        return f"{self.event_type} {self.event_id}"


class AvailabilityRule(models.Model):
    """Recurring weekly availability block for a host's peer sessions."""

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_rules",
    )
    day_of_week = models.PositiveSmallIntegerField(
        choices=[
            (0, _("Monday")),
            (1, _("Tuesday")),
            (2, _("Wednesday")),
            (3, _("Thursday")),
            (4, _("Friday")),
            (5, _("Saturday")),
            (6, _("Sunday")),
        ],
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        verbose_name = _("Availability Rule")
        verbose_name_plural = _("Availability Rules")

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

    @staticmethod
    def get_form_fields():
        return ["day_of_week", "start_time", "end_time", "is_active"]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(_("End time must be after start time."))


class SessionBooking(TimestampedModel, UUIDModel):
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    timezone = models.CharField(max_length=64, default="UTC")
    booking_status = FSMField(default=BookingStatus.PENDING_APPROVAL)
    payment_status = FSMField(default=PaymentStatus.REQUIRED)
    amount_due_subunit = models.PositiveIntegerField(
        default=0,
        help_text=_("Amount due in the subunit of the currency"),
    )
    amount_paid_subunit = models.PositiveIntegerField(
        default=0,
        help_text=_("Amount paid in the subunit of the currency"),
    )
    currency = models.CharField(max_length=3, default="gbp")
    checkout_reference = models.CharField(max_length=255, blank=True)
    accessibility_needs = models.TextField(blank=True)
    intake_response = models.JSONField(null=True, blank=True)
    meeting_link = models.URLField(blank=True)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hosted_bookings",
    )
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendee_bookings",
    )
    session = models.ForeignKey(
        "Session",
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    objects = SessionBookingQuerySet.as_manager()

    class Meta:
        verbose_name = _("Session Booking")
        verbose_name_plural = _("Session Bookings")

    def save(self, *args, **kwargs):
        if (
            self.amount_due_subunit == 0
            and self.payment_status == PaymentStatus.REQUIRED
        ):
            self.payment_status = PaymentStatus.NOT_REQUIRED
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at:
            if self.starts_at >= self.ends_at:
                raise ValidationError(_("End time must be after start time."))
            if self.session_id and self.session.is_peer:
                actual_minutes = (self.ends_at - self.starts_at).total_seconds() / 60
                if (
                    self.session.min_duration_minutes
                    and actual_minutes < self.session.min_duration_minutes
                ):
                    raise ValidationError(
                        _("Minimum booking duration is %(min)s minutes.")
                        % {"min": self.session.min_duration_minutes},
                    )
                if (
                    self.session.max_duration_minutes
                    and actual_minutes > self.session.max_duration_minutes
                ):
                    raise ValidationError(
                        _("Maximum booking duration is %(max)s minutes.")
                        % {"max": self.session.max_duration_minutes},
                    )

    @staticmethod
    def get_form_fields():
        return [
            "currency",
            "accessibility_needs",
            "intake_response",
        ]

    @transition(
        field=booking_status,
        source=BookingStatus.PENDING_APPROVAL,
        target=BookingStatus.APPROVED,
    )
    def approve(self):
        """Host or admin approves a pending booking request."""

    @transition(
        field=booking_status,
        source=BookingStatus.APPROVED,
        target=BookingStatus.CONFIRMED,
        conditions=[
            lambda self: (
                self.payment_status in (PaymentStatus.NOT_REQUIRED, PaymentStatus.PAID)
            ),
            lambda self: not self.session.is_group or self.session.spots_remaining > 0,
            lambda self: not self.session.is_peer or not self._overlaps(),
        ],
    )
    def confirm(self):
        """Finalise an approved booking."""

    @transition(
        field=booking_status,
        source=[
            BookingStatus.PENDING_APPROVAL,
            BookingStatus.APPROVED,
            BookingStatus.CONFIRMED,
        ],
        target=BookingStatus.CANCELLED,
    )
    def cancel(self):
        """Attendee, host or admin cancels a non-terminal booking."""

    @transition(
        field=booking_status,
        source=BookingStatus.CONFIRMED,
        target=BookingStatus.COMPLETED,
    )
    def complete(self):
        """Mark a session as finished."""

    @transition(
        field=booking_status,
        source=BookingStatus.PENDING_APPROVAL,
        target=BookingStatus.EXPIRED,
    )
    def expire_approval(self):
        """Approval window timed out."""

    @transition(
        field=payment_status,
        source=PaymentStatus.REQUIRED,
        target=PaymentStatus.CHECKOUT_CREATED,
        conditions=[lambda self: self.amount_due_subunit > 0],
    )
    def initiate_checkout(self):
        """A Stripe Checkout session has been created for this booking."""

    @transition(
        field=payment_status,
        source=PaymentStatus.CHECKOUT_CREATED,
        target=PaymentStatus.PROCESSING,
    )
    def mark_processing(self):
        """The asynchronous payment is being processed."""

    @transition(
        field=payment_status,
        source=[PaymentStatus.CHECKOUT_CREATED, PaymentStatus.PROCESSING],
        target=PaymentStatus.PAID,
    )
    def mark_paid(self):
        """Payment succeeded. Attempt to confirm the booking."""
        if self.booking_status == BookingStatus.APPROVED:
            with contextlib.suppress(TransitionNotAllowed):
                self.confirm()

    @transition(
        field=payment_status,
        source=[PaymentStatus.CHECKOUT_CREATED, PaymentStatus.PROCESSING],
        target=PaymentStatus.FAILED,
    )
    def mark_failed(self):
        """Payment failed or was declined."""

    @transition(
        field=payment_status,
        source=PaymentStatus.CHECKOUT_CREATED,
        target=PaymentStatus.PROCESSING,
        conditions=[lambda self: self._requires_async_processing()],
    )
    def mark_async_processing(self):
        """Transition to processing for async flows."""

    @transition(
        field=payment_status,
        source=[PaymentStatus.CHECKOUT_CREATED, PaymentStatus.PROCESSING],
        target=PaymentStatus.EXPIRED,
    )
    def expire_payment(self):
        """Payment window timed out."""

    @transition(
        field=payment_status,
        source=PaymentStatus.PAID,
        target=PaymentStatus.REFUND_PENDING_APPROVAL,
        conditions=[lambda self: self.session.require_refund_approval],
    )
    def request_refund(self):
        """A refund request awaiting approval."""

    @transition(
        field=payment_status,
        source=PaymentStatus.PAID,
        target=PaymentStatus.REFUNDED,
        conditions=[lambda self: not self.session.require_refund_approval],
    )
    def auto_refund(self):
        """Refund processed immediately."""

    @transition(
        field=payment_status,
        source=PaymentStatus.REFUND_PENDING_APPROVAL,
        target=PaymentStatus.REFUNDED,
    )
    def approve_refund(self):
        """Admin/host approves the pending refund."""

    @property
    def can_join(self):
        return (
            self.booking_status == BookingStatus.CONFIRMED
            and self.payment_status
            in (
                PaymentStatus.NOT_REQUIRED,
                PaymentStatus.PAID,
            )
        )

    @property
    def approval_required(self):
        return self.session.require_approval

    @property
    def host_stripe_account_id(self):
        return self.host.stripe_account.id if self.host.stripe_account else ""

    @property
    def host_payable_amount_subunit(self):
        return self.amount_due_subunit

    def _overlaps(self):
        return (
            SessionBooking.objects.filter(
                session__host=self.host,
                booking_status=BookingStatus.CONFIRMED,
                starts_at__lt=self.ends_at,
                ends_at__gt=self.starts_at,
            )
            .exclude(pk=self.pk)
            .exists()
        )

    def _requires_async_processing(self):
        return False


auditlog.register(Session)
auditlog.register(SessionBooking)
auditlog.register(SessionPrice)
auditlog.register(Review)
