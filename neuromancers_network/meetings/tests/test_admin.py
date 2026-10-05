import pytest

from neuromancers_network.core.wagtail_hooks import OperationsViewSetGroup
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.meetings.wagtail_hooks import ArchiveMeetingBulkAction
from neuromancers_network.meetings.wagtail_hooks import PublishMeetingBulkAction
from neuromancers_network.meetings.wagtail_hooks import UnpublishMeetingBulkAction
from neuromancers_network.peers.tests.factories import make_peer

pytestmark = pytest.mark.django_db


class TestMeetingBulkActions:
    def test_publish_draft(self):
        meeting = create_meeting(peer=make_peer(), status=MeetingStatus.DRAFT)

        PublishMeetingBulkAction.execute_action([meeting])

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.PUBLISHED

    def test_unpublish_published(self):
        meeting = create_meeting(peer=make_peer(), status=MeetingStatus.PUBLISHED)

        UnpublishMeetingBulkAction.execute_action([meeting])

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.DRAFT

    def test_archive_published(self):
        meeting = create_meeting(peer=make_peer(), status=MeetingStatus.PUBLISHED)

        ArchiveMeetingBulkAction.execute_action([meeting])

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.ARCHIVED


class TestOperationsGroup:
    def test_group_collects_viewsets(self):
        labels = {
            str(viewset.menu_label)
            for viewset in OperationsViewSetGroup().registerables
        }

        assert {
            "Peer applications",
            "Meetings",
            "Bookings",
            "Price tiers",
            "Allowed tags",
            "Webhook endpoints",
        } <= labels
