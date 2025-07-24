import uuid

from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    int_list_validator,
)
from django.db import models

from apps.accounts.models import User


class Session(models.Model):
    """
    These are types of events that can be provided and managed by `Peer` and `Admin` users and scheduled by `SupportSeeker` users.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=320)
    description = models.TextField()
    durations = models.CharField(
        help_text="These are durations (in minutes) that a session may be booked for",
        max_length=320,
        validators=[int_list_validator(sep=",", message=("Only digits allowed"))],
    )
    is_published = models.BooleanField(default=False)
    provider = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        permissions = [
            ("can_provide_sessions", "Can provide a session to support seekers"),
            ("can_view_sessions", "Can view a session"),
            ("can_manage_sessions", "Can manage all sessions"),
        ]

    def __str__(self):
        return self.title


class SessionAvailability(models.Model):
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="availabilities"
    )

    class Meta:
        unique_together = ("session", "starts_at")  # Optional: prevent duplicate slots

    def __str__(self):
        return f"{self.start_at} - {self.end_at}"


class ScheduledEvent(models.Model):
    """
    These are scheduled events that can be provided and managed by `Peer` and `Admin` users and scheduled by `SupportSeeker` users.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=320)
    description = models.TextField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.IntegerField(
        help_text="Number of people that can attend this session",
        default=1,
        validators=[MaxValueValidator(100), MinValueValidator(1)],
    )
    is_published = models.BooleanField(default=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    attendees = models.ManyToManyField(User)

    class Meta:
        permissions = [
            (
                "can_provide_scheduled_events",
                "Can provide a scheduled event to support seekers",
            ),
            ("can_schedule_events", "Can schedule an event"),
            ("can_manage_scheduled_events", "Can manage all scheduled events"),
        ]

    def __str__(self):
        return self.title
