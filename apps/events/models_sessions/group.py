from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from wagtail.contrib.settings.registry import registry

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "host"):
            self._initial_host = self.host
        if hasattr(self, "filters"):
            self._initial_filters = self.filters

    @cached_property
    def currency_symbol(self):
        _currency = filtered_currencies.get(self.currency, None)

        if not _currency:
            return ""

        return _currency.get("symbol", None)

    @cached_property
    def attendees(self):
        """
        Gets attendees based on users who have requested to join and have been approved
        """
        return self.support_seekers.filter(
            requests__status=SessionRequestStatusChoices.APPROVED
        )

    @cached_property
    def language_display(self):
        all_languages = get_languages()
        return all_languages.get(self.language)

    def attendee_requested(self, user):
        return self.requests.filter(
            attendee=user,
            status__in=[
                SessionRequestStatusChoices.PENDING,
                SessionRequestStatusChoices.APPROVED,
            ],
        ).exists()

    def attendee_approved(self, user):
        return self.requests.filter(
            attendee=user, status=SessionRequestStatusChoices.APPROVED
        ).exists()

    def get_pending_request(self, user):
        """Return the user's pending request for this session, if any."""
        return (
            self.requests.filter(
                attendee=user, status=SessionRequestStatusChoices.PENDING
            )
            .order_by("-created_at")
            .first()
        )

    def save(self, *args, **kwargs):
        if not self._state.adding and self._initial_host.pk != self.host.pk:
            raise ValidationError(_("Session host cannot be changed after creation"))
        else:
            can_add = self.host.has_perm("events.add_groupsession")

            if not can_add:
                return

        # Convert list of grouped filters to JSON
        # This allows the admin interface to work with the grouped checkbox widget
        # List format: ['group::item', ...]
        if isinstance(self.filters, list):
            # Load registry object and get current filter settings to validate against
            filter_settings = registry.get_by_natural_key(
                "events", "FilterSettings"
            ).load()
            filters_mapping = filter_settings.get_cached_mapping()

            normalized_filters = {}

            for filter_str in self.filters:
                try:
                    group_slug, item_slug = filter_str.split("::")
                except ValueError:
                    continue  # skip invalid format

                group = filters_mapping.get(group_slug)
                if not group:
                    continue  # skip invalid group

                item = group["items"].get(item_slug)
                if not item:
                    continue  # skip invalid item

                if group_slug not in normalized_filters:
                    normalized_filters[group_slug] = {"items": {}}

                normalized_filters[group_slug]["items"][item_slug] = {}

            # Merge normalized filters with existing filters to preserve any additional data
            if self._initial_filters:
                if not isinstance(self._initial_filters, dict):
                    self._initial_filters = {}
                existing = self._initial_filters
                for group_slug, group_data in normalized_filters.items():
                    if group_slug not in existing:
                        existing[group_slug] = group_data
                    else:
                        existing[group_slug]["items"].update(group_data["items"])
                self.filters = existing
            else:
                self.filters = normalized_filters

            self._initial_filters = (
                self.filters
            )  # Update initial filters after normalization

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "session"):
            self._initial_session = self.session
        if hasattr(self, "attendee"):
            self._initial_attendee = self.attendee

    def __str__(self):
        return f"{self.session.title} for {self.attendee.username}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            if self._initial_attendee.pk != self.attendee.pk:
                raise ValidationError(
                    _("Session attendee cannot be changed after creation")
                )

            if self._initial_session.pk != self.session.pk:
                raise ValidationError(_("Session cannot be changed after creation"))

        if not self.attendee.has_perm("request_join_session", self.session):
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
    attended_request = models.OneToOneField(
        GroupSessionRequest, on_delete=models.CASCADE, related_name="review"
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_attended_session = self.attended_session
        self._initial_attendee = self.attendee
        self._initial_attended_request = self.attended_request

    def save(self, *args, **kwargs):
        if not self._state.adding:
            if self._initial_attended_session.pk != self.attended_session.pk:
                raise ValidationError(
                    _("Attended session cannot be changed after creation")
                )

            if self._initial_attendee.pk != self.attendee.pk:
                raise ValidationError(_("Attendee cannot be changed after creation"))

            if self._initial_attended_request.pk != self.attended_request.pk:
                raise ValidationError(
                    _("Attended request cannot be changed after creation")
                )
        else:
            approved_request = (
                self.attended_request.status == SessionRequestStatusChoices.APPROVED
            )
            now_after_session = timezone.now() >= self.attended_request.ends_at

            if not approved_request or not now_after_session:
                return

        super().save(*args, **kwargs)
