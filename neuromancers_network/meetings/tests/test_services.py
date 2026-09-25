import pytest
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError

from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.services import create_meeting
from neuromancers_network.meetings.services import publish_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.taxonomy.tests.factories import AllowedTagFactory
from neuromancers_network.taxonomy.tests.factories import CountryFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def meeting_fields() -> dict:
    return {
        "title": "Session",
        "description": "A test meeting",
        "meeting_type": MeetingType.ONE_ON_ONE,
        "pricing_type": PricingType.FIXED,
        "price": 25,
        "approval_policy": ApprovalPolicy.PAY_AFTER_JOIN,
        "currency": "GBP",
    }


class TestCreateMeeting:
    def test_ineligible_peer_is_rejected(self):
        peer = UserFactory()

        with pytest.raises(PermissionDenied):
            create_meeting(peer=peer, **meeting_fields())

    def test_eligible_peer_creates_draft_with_default_terms(self):
        peer = make_peer(default_terms="Be kind")

        meeting = create_meeting(peer=peer, **meeting_fields())

        assert meeting.status == MeetingStatus.DRAFT
        assert meeting.terms == "Be kind"

    def test_explicit_terms_are_kept(self):
        peer = make_peer(default_terms="Default")

        meeting = create_meeting(peer=peer, terms="Custom", **meeting_fields())

        assert meeting.terms == "Custom"


class TestCreateMeetingTaxonomy:
    def test_unknown_tag_is_rejected(self):
        peer = make_peer()

        with pytest.raises(ValidationError):
            create_meeting(peer=peer, tags=["unknown"], **meeting_fields())

    def test_inactive_tag_is_rejected(self):
        peer = make_peer()
        AllowedTagFactory(name="retired", is_active=False)

        with pytest.raises(ValidationError):
            create_meeting(peer=peer, tags=["retired"], **meeting_fields())

    def test_unknown_country_is_rejected(self):
        peer = make_peer()

        with pytest.raises(ValidationError):
            create_meeting(peer=peer, countries=["ZZ"], **meeting_fields())

    def test_valid_tag_and_country_are_set(self):
        peer = make_peer()
        tag = AllowedTagFactory(name="anxiety")
        country = CountryFactory()

        meeting = create_meeting(
            peer=peer,
            tags=[tag],
            countries=[country],
            **meeting_fields(),
        )

        assert list(meeting.tags.all()) == [tag]
        assert list(meeting.countries.all()) == [country]


class TestPublishMeeting:
    def test_publish_transitions_to_published(self):
        peer = make_peer()
        meeting = create_meeting(peer=peer, **meeting_fields())

        publish_meeting(meeting)

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.PUBLISHED
