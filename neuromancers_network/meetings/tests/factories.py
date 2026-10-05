from decimal import Decimal

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.taxonomy.models import AllowedTag
from neuromancers_network.taxonomy.tests.factories import ensure_tag


def resolve_tags(tags) -> list[AllowedTag]:
    """Resolve tag names or ``AllowedTag`` instances into tag instances."""
    resolved = []
    for tag in tags:
        if isinstance(tag, AllowedTag):
            resolved.append(tag)
        else:
            resolved.append(ensure_tag(tag))
    return resolved


def create_meeting(  # noqa: PLR0913
    peer,
    *,
    title="Meeting",
    languages=(),
    tags=(),
    countries=(),
    status=MeetingStatus.PUBLISHED,
) -> Meeting:
    """
    Create a Meeting for tests.

    ``Meeting.save()`` validates via ``full_clean()``, which django-fsm's
    protected ``status`` field rejects, so the instance is saved with
    ``validate=False`` and status set only at construction time.
    """
    meeting = Meeting(
        peer=peer,
        title=title,
        description="Test description",
        meeting_type=MeetingType.ONE_ON_ONE,
        pricing_type=PricingType.FIXED,
        price=Decimal("25.00"),
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        currency="GBP",
        status=status,
    )
    meeting.save(validate=False)
    meeting.languages.set(languages)
    meeting.countries.set(countries)
    meeting.tags.add(*resolve_tags(tags))
    return meeting
