from datetime import timedelta

from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext as _
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm, remove_perm

from apps.accounts.models import UserGroup
from apps.events.choices import SessionRequestStatusChoices, filtered_currencies
from apps.events.utils import get_languages

from .abstract import AbstractSession, AbstractSessionRequest, User


class GroupSession(AbstractSession):
    """
    Group sessions cannot be requested but may attended by several `SupportSeeker` users for a single duration of time
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
                    "Published sessions must be unique. Unpublish existing sessions with the same title or change the title of this session."
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
        ]

        permissions = [
            ("request_join_session", "Request join session"),
        ]

    @property
    def currency_symbol(self):
        _currency = filtered_currencies.get(self.currency, None)

        if not _currency:
            return ""

        return _currency.get("symbol", None)

    @property
    def attendees(self):
        """
        Gets attendees based on support seekers who have requested to join and have been approved
        """
        return self.support_seekers.filter(
            requests__status=SessionRequestStatusChoices.APPROVED
        )

    @property
    def language_display(self):
        all_languages = get_languages()
        return all_languages.get(self.language)

    def save(self, *args, **kwargs):
        support_seeker_group = UserGroup.objects.get(name="Support Seeker")

        if not support_seeker_group:
            return

        super().save(*args, **kwargs)
        support_seeker_perms = [
            "events.view_groupsession",
            "events.request_join_session",
        ]
        for perm in support_seeker_perms:
            if self.is_published:
                assign_perm(perm, support_seeker_group, self)
            else:
                remove_perm(perm, support_seeker_group, self)

        perms = [
            "events.change_groupsession",
            "events.delete_groupsession",
            "events.view_groupsession",
        ]

        if self.host:
            for perm in perms:
                assign_perm(perm, self.host, self)

        super().save(*args, **kwargs)

    def attendee_requested(self, user):
        return self.requests.filter(attendee=user).exists()

    def attendee_approved(self, user):
        return self.requests.filter(
            attendee=user, status=SessionRequestStatusChoices.APPROVED
        ).exists()


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

    def __str__(self):
        return f"{self.session.title} for {self.attendee.username}"

    def save(self, *args, **kwargs):
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
