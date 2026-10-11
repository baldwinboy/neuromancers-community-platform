import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from neuromancers_network.meetings.actions import meetings_delete
from neuromancers_network.meetings.actions import meetings_publish
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.selectors import my_meetings
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.meetings.wagtail_hooks import ArchiveMeetingBulkAction
from neuromancers_network.meetings.wagtail_hooks import PublishMeetingBulkAction
from neuromancers_network.meetings.wagtail_hooks import UnpublishMeetingBulkAction
from neuromancers_network.peers.tests.factories import make_peer

pytestmark = pytest.mark.django_db


def _request(user):
    request = RequestFactory().post("/", {})
    request.user = user
    return request


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


class TestMeetingManageActions:
    def test_publish_owned_meeting(self):
        meeting = create_meeting(peer=make_peer(), status=MeetingStatus.DRAFT)

        meetings_publish(_request(meeting.peer), {"target": meeting.pk})

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.PUBLISHED

    def test_delete_requires_ownership(self):
        meeting = create_meeting(peer=make_peer())

        with pytest.raises(PermissionDenied):
            meetings_delete(_request(make_peer()), {"target": meeting.pk})

    def test_owner_can_delete(self):
        meeting = create_meeting(peer=make_peer())

        meetings_delete(_request(meeting.peer), {"target": meeting.pk})

        assert not type(meeting).objects.filter(pk=meeting.pk).exists()


class TestMyMeetings:
    def test_returns_only_signed_in_users_meetings(self):
        peer = make_peer()
        mine = create_meeting(peer=peer, title="Mine")
        create_meeting(peer=make_peer(), title="Theirs")

        results = my_meetings(request=_request(peer))

        assert list(results) == [mine]

    def test_anonymous_sees_nothing(self):
        create_meeting(peer=make_peer())
        anonymous = RequestFactory().get("/")
        anonymous.user = type("Anon", (), {"is_authenticated": False})()

        assert list(my_meetings(request=anonymous)) == []
