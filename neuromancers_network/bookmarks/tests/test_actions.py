from __future__ import annotations

import pytest
from django.test import RequestFactory

from neuromancers_network.bookmarks.actions import toggle_meeting
from neuromancers_network.bookmarks.actions import toggle_peer
from neuromancers_network.meetings.models import MeetingsBookmark
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.models import PeersBookmark
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _request(user):
    request = RequestFactory().post("/")
    request.user = user
    return request


def test_toggle_peer_is_idempotent():
    user = UserFactory()
    peer = make_peer()
    request = _request(user)

    toggle_peer(request, {"peer": peer.peer_profile.pk})
    bookmark = PeersBookmark.objects.get(user=user)
    assert bookmark.peers.filter(pk=peer.peer_profile.pk).exists()

    toggle_peer(request, {"peer": peer.peer_profile.pk})
    bookmark.refresh_from_db()
    assert not bookmark.peers.exists()


def test_toggle_meeting_is_user_scoped():
    user = UserFactory()
    other = UserFactory()
    meeting = create_meeting(peer=make_peer())

    toggle_meeting(_request(user), {"meeting": meeting.pk})

    assert MeetingsBookmark.objects.filter(user=user).exists()
    assert not MeetingsBookmark.objects.filter(user=other).exists()
