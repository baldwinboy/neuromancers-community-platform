from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext as _
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from apps.events.choices import (
    GroupSessionOccurrenceChoices,
    SessionRequestStatusChoices,
    filtered_currencies,
)
from apps.events.utils import get_languages

from .abstract import (
    AbstractSession,
    AbstractSessionRequest,
    AbstractSessionReview,
    User,
)


class GroupSession(AbstractSession):
    """
    Group sessions cannot be requested but may be attended by
    several users for a single duration of time.
    Session host cannot be changed after creation.
    """

    language = models.CharField(
        choices=get_languages,
        help_text=_("This is the language that the session will be provided in"),
        max_length=2,
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveSmallIntegerField(
        help_text=_("Number of people that can attend at this time"),
        default=1,
    )
    is_published = models.BooleanField(default=False)
    meeting_link = models.URLField(
        help_text=_("This will be automatically generated if not set"),
        null=True,
        blank=True,
    )

    recurring = models.BooleanField(default=False)

    recurrence_type = models.CharField(
        max_length=10,
        choices=GroupSessionOccurrenceChoices,
        null=True,
        blank=True,
    )
    recurrence_ends_at = models.DateTimeField(
        null=True, blank=True, help_text=_("Leave blank for indefinite recurrence")
    )

    support_seekers = models.ManyToManyField(
        User,
        through="GroupSessionRequest",
        related_name="requested_sessions",
        blank=True,
    )
    host = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="group_sessions"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["host", "title", "is_published"],
                name="unique_published_group_session",
                violation_error_message=_(
                    "Published sessions must be unique. Unpublish existing"
                    "  sessions with the same title before publishing a new one."
                ),
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gte=(F("starts_at") + timedelta(minutes=5)))
                & Q(ends_at__lte=(F("starts_at") + timedelta(minutes=120))),
                name="group_ends_at_gte_starts_at",
                violation_error_message=_(
                    "Group session must last between 5 and 120 minutes"
                ),
            ),
            models.CheckConstraint(
                # If the session is free, access before payment can't be withheld
                condition=Q(price__gt=0) | Q(access_before_payment=True),
                name="group_access_before_payment_price_zero",
                violation_error_message=_(
                    "Free sessions can't require access before payment"
                ),
            ),
            models.CheckConstraint(
                condition=Q(recurring=True, recurrence_type__isnull=False)
                | Q(recurring=False, recurrence_type__isnull=True),
                name="event_recurrence_type_required_if_recurring",
                violation_error_message=_(
                    "Events can occur repeatedly only if you set both "
                    "recurring and recurrence type"
                ),
            ),
        ]

        permissions = [
            ("request_join_session", "Request join session"),
        ]

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)

        # save original values, when model is loaded from database,
        # in a separate attribute on the model
        instance._loaded_values = dict(zip(field_names, values))

        return instance

    @property
    def currency_symbol(self):
        _currency = filtered_currencies.get(self.currency, None)

        if not _currency:
            return ""

        return _currency.get("symbol", None)

    @property
    def attendees(self):
        """
        Gets attendees based on users who have requested to join and have been approved
        """
        return self.support_seekers.filter(
            requests__status=SessionRequestStatusChoices.APPROVED
        )

    @property
    def language_display(self):
        all_languages = get_languages()
        return all_languages.get(self.language)

    def attendee_requested(self, user):
        return self.requests.filter(attendee=user).exists()

    def attendee_approved(self, user):
        return self.requests.filter(
            attendee=user, status=SessionRequestStatusChoices.APPROVED
        ).exists()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            # Prevent changes to host after creation (using cached values from from_db)
            loaded_values = getattr(self, "_loaded_values", {})
            if loaded_values.pop("host_id", None) != self.host_id:
                raise ValidationError(
                    _("Session host cannot be changed after creation")
                )
        else:
            can_add = self.host.has_perm("events.add_groupsession")

            if not can_add:
                return

        super().save(*args, **kwargs)


class GroupSessionUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(GroupSession, on_delete=models.CASCADE)


class GroupSessionGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(GroupSession, on_delete=models.CASCADE)


class GroupSessionRequest(AbstractSessionRequest):
    """
    Group session requests represent Support Seekers joining a group session.
    Session and attendee relations cannot be changed after creation.
    Only the session host can approve/withdraw (inferred from session permissions).
    """

    attendee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="group_session_requests"
    )
    session = models.ForeignKey(
        GroupSession, on_delete=models.CASCADE, related_name="requests"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attendee", "session"],
                name="unique_group_request",
                violation_error_message=_(
                    "Attendees may only request once per session."
                ),
            ),
        ]

        permissions = [
            ("approve_group_request", "Approve group request"),
            ("withdraw_group_request", "Withdraw group request"),
        ]

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)

        # save original values, when model is loaded from database,
        # in a separate attribute on the model
        instance._loaded_values = dict(zip(field_names, values))

        return instance

    def __str__(self):
        return f"{self.session.title} for {self.attendee.username}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            # Use cached values from from_db() for efficient validation
            loaded_values = getattr(self, "_loaded_values", {})

            if loaded_values.pop("attendee_id", None) != self.attendee_id:
                raise ValidationError(_("Attendee cannot be changed after creation"))

            if loaded_values.pop("session_id", None) != self.session_id:
                raise ValidationError(_("Session cannot be changed after creation"))

        if (
            not self.attendee
            or not self.session
            or not self.session.host
            or not self.attendee.has_perm("events.request_join_session")
        ):
            return

        if (
            not self.session.require_request_approval
            and self.status == SessionRequestStatusChoices.PENDING
        ):
            self.status = SessionRequestStatusChoices.APPROVED

        super().save(*args, **kwargs)


class GroupSessionRequestUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(GroupSessionRequest, on_delete=models.CASCADE)


class GroupSessionRequestGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(GroupSessionRequest, on_delete=models.CASCADE)


class GroupSessionReview(AbstractSessionReview):
    attended_session = models.ForeignKey(
        GroupSession, on_delete=models.CASCADE, related_name="reviews"
    )
    attendee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="group_session_reviews"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attended_session", "attendee"],
                name="unique_group_session_review",
                violation_error_message=_(
                    "You can only leave one review on each group session you've attended"
                ),
            ),
        ]

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)

        # save original values, when model is loaded from database,
        # in a separate attribute on the model
        instance._loaded_values = dict(zip(field_names, values))

        return instance

    def save(self, *args, **kwargs):
        if not self._state.adding:
            # Use cached values from from_db() for efficient validation
            loaded_values = getattr(self, "_loaded_values", {})

            if loaded_values.pop("attendee_id", None) != self.attendee_id:
                raise ValidationError(_("Attendee cannot be changed after creation"))

            if (
                loaded_values.pop("attended_session_id", None)
                != self.attended_session_id
            ):
                raise ValidationError(
                    _("Attended session cannot be changed after creation")
                )

        super().save(*args, **kwargs)
