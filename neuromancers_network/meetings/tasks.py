from datetime import timedelta

from celery import shared_task
from django.utils import timezone


@shared_task
def populate_pending_meeting_links():
    """
    For MeetingRequests within the next hour that have no meeting_link,
    create a Whereby room and populate the link.
    Applies to 1:1 meetings only (group meetings get links on creation).
    """
    from .models import MeetingRequest  # noqa: PLC0415

    now = timezone.now()
    threshold = now + timedelta(hours=1)

    requests = MeetingRequest.objects.filter(
        meeting_link="",
        meeting__meeting_type="1:1",
        requested_start_time__lte=threshold,
        requested_start_time__gte=now,
        status__in=["paid", "approved"],
    )

    for req in requests:
        req.populate_meeting_link()


@shared_task
def populate_pending_group_meeting_links():
    """Populate missing Whereby links for soon-starting group meetings."""
    from .models import Meeting  # noqa: PLC0415
    from .models import MeetingType  # noqa: PLC0415

    now = timezone.now()
    threshold = now + timedelta(minutes=10)

    meetings = Meeting.objects.filter(
        meeting_link="",
        meeting_type=MeetingType.GROUP,
        scheduled_at__gte=now,
        scheduled_at__lte=threshold,
    )

    for meeting in meetings:
        meeting.populate_meeting_link()


@shared_task
def mark_completed_sessions():
    """Mark paid sessions whose start time has passed as completed."""
    from .models import MeetingRequest  # noqa: PLC0415
    from .models import MeetingRequestStatus  # noqa: PLC0415

    now = timezone.now()
    sessions = MeetingRequest.objects.filter(
        status=MeetingRequestStatus.PAID,
        requested_start_time__isnull=False,
        requested_start_time__lt=now,
    )

    for session in sessions:
        session.complete()
        session.save(validate=False, update_fields=["status", "updated_at"])


@shared_task
def generate_recurring_group_meetings():
    """
    Look for group meetings with a recurrence_rule whose scheduled_at
    is in the past and create the next occurrence.

    For each generated meeting a Whereby link is created automatically.
    The source meeting is advanced via ``RecurrenceRule.advance_meeting``
    so that subsequent task runs compute the correct next slot.
    """
    from .models import Meeting  # noqa: PLC0415
    from .models import MeetingStatus  # noqa: PLC0415
    from .models import MeetingType  # noqa: PLC0415

    now = timezone.now()

    past_group_meetings = Meeting.objects.filter(
        meeting_type=MeetingType.GROUP,
        recurrence_rule__isnull=False,
        scheduled_at__lt=now,
    )

    for meeting in past_group_meetings:
        rule = meeting.recurrence_rule
        if not rule:
            continue

        existing_count = (
            Meeting.objects.filter(
                recurrence_rule=rule,
                peer=meeting.peer,
            )
            .exclude(pk=meeting.pk)
            .count()
        )

        if rule.max_occurrences and existing_count >= rule.max_occurrences:
            continue

        if (
            rule.end_date
            and meeting.scheduled_at
            and meeting.scheduled_at.date() >= rule.end_date
        ):
            continue

        next_scheduled = rule.compute_next_occurrence(meeting.scheduled_at)
        if next_scheduled is None:
            continue

        if rule.end_date and next_scheduled.date() > rule.end_date:
            continue

        new_meeting = Meeting.objects.create(
            peer=meeting.peer,
            title=meeting.title,
            description=meeting.description,
            meeting_type=meeting.meeting_type,
            pricing_type=meeting.pricing_type,
            price=meeting.price,
            sliding_scale_min=meeting.sliding_scale_min,
            sliding_scale_max=meeting.sliding_scale_max,
            currency=meeting.currency,
            approval_policy=meeting.approval_policy,
            max_participants=meeting.max_participants,
            recurrence_rule=rule,
            scheduled_at=next_scheduled,
            duration_minutes=meeting.duration_minutes,
            status=MeetingStatus.PUBLISHED,
        )
        new_meeting.languages.set(meeting.languages.all())
        new_meeting.populate_meeting_link()
        rule.advance_meeting(meeting)
