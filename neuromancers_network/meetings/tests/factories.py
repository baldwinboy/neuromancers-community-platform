from decimal import Decimal

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType


def create_meeting(
    peer,
    *,
    title="Meeting",
    languages=(),
    tags=(),
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
    meeting.tags.add(*tags)
    return meeting
