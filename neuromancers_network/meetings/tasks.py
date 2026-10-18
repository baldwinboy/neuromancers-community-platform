from datetime import timedelta

from celery import shared_task
from django.utils import timezone


@shared_task
def populate_pending_meeting_links():
    """
    For MeetingRequests within the next hour that have no meeting_link,
    create a meeting room and populate the link.
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
    """Populate missing meeting links for soon-starting group meetings."""
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


def next_publishable_slot(rule, after, *, minimum):
    """Return the first recurrence slot at or after *minimum*.

    Slots in the past or within the group-meeting lead time are skipped so the
    generated occurrence always passes ``Meeting.clean()``. Returns ``None`` when
    the rule has ended.
    """
    next_slot = rule.compute_next_occurrence(after)
    for _ in range(1000):
        if rule.end_date and next_slot.date() > rule.end_date:
            return None
        if next_slot >= minimum:
            return next_slot
        next_slot = rule.compute_next_occurrence(next_slot)
    return None


@shared_task
def generate_recurring_group_meetings():
    """Create the next occurrence for each recurring group-meeting series.

    A series is the ``(recurrence_rule, peer)`` pair. Generation is keyed on the
    next publishable slot (unique per rule/peer/slot), so repeated runs are
    idempotent and the source occurrence is never advanced.
    """
    from django.db.models import Count  # noqa: PLC0415
    from django.db.models import Max  # noqa: PLC0415

    from .models import Meeting  # noqa: PLC0415
    from .models import MeetingStatus  # noqa: PLC0415
    from .models import MeetingType  # noqa: PLC0415
    from .models import RecurrenceRule  # noqa: PLC0415
    from .models.meeting import GROUP_MINIMUM_START_AHEAD_MINUTES  # noqa: PLC0415

    now = timezone.now()
    minimum = now + timedelta(minutes=GROUP_MINIMUM_START_AHEAD_MINUTES)
    series = (
        Meeting.objects.filter(
            meeting_type=MeetingType.GROUP,
            status=MeetingStatus.PUBLISHED,
            recurrence_rule__isnull=False,
            scheduled_at__isnull=False,
        )
        .order_by()
        .values("recurrence_rule_id", "peer_id")
        .annotate(last_scheduled=Max("scheduled_at"), occurrences=Count("pk"))
    )

    for row in series:
        if row["last_scheduled"] >= now:
            continue

        rule = RecurrenceRule.objects.filter(pk=row["recurrence_rule_id"]).first()
        if rule is None:
            continue
        if rule.max_occurrences and row["occurrences"] >= rule.max_occurrences:
            continue

        next_scheduled = next_publishable_slot(
            rule,
            row["last_scheduled"],
            minimum=minimum,
        )
        if next_scheduled is None:
            continue

        latest = (
            Meeting.objects.filter(
                recurrence_rule_id=row["recurrence_rule_id"],
                peer_id=row["peer_id"],
                status=MeetingStatus.PUBLISHED,
            )
            .order_by("-scheduled_at")
            .first()
        )
        if latest is None:
            continue

        meeting, created = Meeting.objects.get_or_create(
            recurrence_rule=rule,
            peer_id=row["peer_id"],
            scheduled_at=next_scheduled,
            defaults={
                "title": latest.title,
                "description": latest.description,
                "meeting_type": latest.meeting_type,
                "pricing_type": latest.pricing_type,
                "price": latest.price,
                "sliding_scale_min": latest.sliding_scale_min,
                "sliding_scale_max": latest.sliding_scale_max,
                "currency": latest.currency,
                "approval_policy": latest.approval_policy,
                "max_participants": latest.max_participants,
                "duration_minutes": latest.duration_minutes,
                "status": MeetingStatus.PUBLISHED,
            },
        )
        if not created:
            continue
        meeting.languages.set(latest.languages.all())
        meeting.countries.set(latest.countries.all())
        meeting.tags.set(latest.tags.all())
