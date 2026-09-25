from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.peers.models import PeerProfile
from neuromancers_network.users.tests.factories import UserFactory


def make_peer(*, approved=True):
    profile = PeerProfile.objects.create(user=UserFactory())
    if approved:
        profile.is_approved = True
        profile.approved_by = UserFactory(is_staff=True)
        profile.save()
    return profile.user


def make_meeting(
    peer,
    *,
    meeting_type=MeetingType.ONE_ON_ONE,
    approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
    status=MeetingStatus.PUBLISHED,
    refund_requires_approval=True,
):
    kwargs = {}
    if meeting_type == MeetingType.GROUP:
        kwargs.update(
            {
                "scheduled_at": timezone.now() + timedelta(hours=2),
                "duration_minutes": 60,
                "max_participants": 10,
            },
        )
    meeting = Meeting(
        peer=peer,
        title="Test meeting",
        description="Test description",
        meeting_type=meeting_type,
        pricing_type=PricingType.FIXED,
        price=Decimal("25.00"),
        approval_policy=approval_policy,
        refund_requires_approval=refund_requires_approval,
        currency="GBP",
        status=status,
        **kwargs,
    )
    meeting.save(validate=False)
    return meeting


def make_request(
    meeting,
    seeker=None,
    *,
    requested_start_time=None,
):
    if seeker is None:
        seeker = UserFactory()
    return MeetingRequest.objects.create(
        meeting=meeting,
        support_seeker=seeker,
        requested_start_time=requested_start_time,
    )
