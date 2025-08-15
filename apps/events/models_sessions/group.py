from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext as _
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from apps.events.choices import SessionRequestStatusChoices

from .abstract import AbstractSession, AbstractSessionRequest, User


class GroupSession(AbstractSession):
    """
    Group sessions cannot be requested but may attended by several `SupportSeeker` users for a single duration of time
    """

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
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gte=(F("starts_at") + timedelta(minutes=5))),
                name="group_ends_at_gte_starts_at",
                violation_error_message=_("Group session must last at least 5 minutes"),
            ),
            models.CheckConstraint(
                # If the session is free, access before payment can't be withheld
                condition=Q(price=0, access_before_payment=False) | ~Q(price=0),
                name="group_access_before_payment_price_zero",
                violation_error_message=_(
                    "Free sessions can't require access before payment"
                ),
            ),
        ]

        permissions = [
            ("request_join_session", "Request join session"),
        ]

    def validate_unique(self, *args, **kwargs):
        """
        Published group sessions should not conflict with existing published group sessions from the same host
        """
        overlapping_requests = GroupSession.objects.filter(
            Q(starts_at__lt=self.ends_at, ends_at__gt=self.starts_at)
            | Q(starts_at__gte=self.starts_at, ends_at__lte=self.ends_at),
            host=self.host,
            is_published=True,
        )

        if overlapping_requests.exists():
            raise ValidationError(
                _(
                    "Published group sessions should not conflict with existing published group sessions from the same host"
                )
            )

        super(GroupSession, self).validate_unique(*args, **kwargs)

    def get_attendees(self):
        """
        Gets attendees based on support seekers who have requested to join and have been approved
        """
        return self.support_seekers.filter(
            requests__status=SessionRequestStatusChoices.APPROVED
        )


class GroupSessionUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(GroupSession, on_delete=models.CASCADE)


class GroupSessionGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(GroupSession, on_delete=models.CASCADE)


class GroupSessionRequest(AbstractSessionRequest):
    attendee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="group_session_requests"
    )
    session = models.ForeignKey(
        GroupSession, on_delete=models.CASCADE, related_name="requests"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attendee", "session"], name="unique_group_request"
            )
        ]

    def __str__(self):
        return f"{self.session.title} for {self.attendee.username}"


class GroupSessionRequestUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(GroupSessionRequest, on_delete=models.CASCADE)


class GroupSessionRequestGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(GroupSessionRequest, on_delete=models.CASCADE)
