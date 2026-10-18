from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from wagtail.models import Page

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models.pages import MeetingDetailPage
from neuromancers_network.core.models.pages import MeetingIndexPage
from neuromancers_network.core.models.pages import PeerProfileDetailPage
from neuromancers_network.core.models.pages import ReviewDetailPage
from neuromancers_network.core.models.pages import UserProfilePage
from neuromancers_network.core.wagtail_hooks import hide_inaccessible_detail_pages
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import Review
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

NOT_FOUND = 404


def _home() -> HomePage:
    home = HomePage.objects.first()
    if home is None:
        root = Page.get_first_root_node()
        home = HomePage(title="Home", slug="home")
        root.add_child(instance=home)
    return home


def _request(user=None):
    request = RequestFactory().get("/")
    request.user = user or AnonymousUser()
    return request


def _review() -> Review:
    reviewed = make_peer()
    reviewer = UserFactory()
    meeting = create_meeting(peer=reviewed)
    booking = create_booking(
        meeting=meeting,
        seeker=reviewer,
        sessions=[{"requested_duration_minutes": 30}],
    )
    return Review.objects.create(
        meeting_request=booking.sessions.first(),
        reviewer=reviewer,
        peer=reviewed,
        rating=5,
    )


class TestDetailContextBinding:
    def test_meeting_detail_binds_its_own_source_only(self):
        _home()
        meeting = create_meeting(peer=make_peer())
        page = MeetingDetailPage.objects.get(source_object_id=meeting.pk).specific

        context = page.get_context(_request())

        assert context["meeting"] == meeting
        assert "peer_profile" not in context
        assert "review" not in context

    def test_owner_sees_unpublished_meeting(self):
        _home()
        peer = make_peer()
        meeting = create_meeting(peer=peer)
        meeting.status = MeetingStatus.DRAFT
        meeting.save(validate=False)
        page = MeetingDetailPage.objects.get(source_object_id=meeting.pk).specific

        context = page.get_context(_request(peer))

        assert context["meeting"] == meeting

    def test_peer_profile_detail_binds_peer(self):
        _home()
        peer = make_peer()
        profile = peer.peer_profile
        page = PeerProfileDetailPage.objects.get(source_object_id=profile.pk).specific

        context = page.get_context(_request())

        assert context["peer_profile"] == profile
        assert "meeting" not in context

    def test_review_detail_binds_review(self):
        _home()
        review = _review()
        page = ReviewDetailPage.objects.get(source_object_id=review.pk).specific

        context = page.get_context(_request())

        assert context["review"] == review
        assert "meeting" not in context

    def test_user_profile_detail_binds_profile(self):
        _home()
        user = UserFactory()
        profile, _created = UserProfile.objects.get_or_create(user=user)
        page = UserProfilePage.objects.get(source_object_id=user.pk).specific

        context = page.get_context(_request())

        assert context["user_profile"] == profile

    def test_path_params_are_replaced_not_merged(self):
        _home()
        meeting = create_meeting(peer=make_peer())
        page = MeetingDetailPage.objects.get(source_object_id=meeting.pk).specific
        request = _request()
        request.daisie_path_params = {"stale": "1"}

        page.get_context(request)

        assert "stale" not in request.daisie_path_params
        assert request.daisie_path_params["meeting_pk"] == meeting.pk


class TestDetailVisibility:
    def test_orphaned_page_returns_404(self):
        _home()
        meeting = create_meeting(peer=make_peer())
        page = MeetingDetailPage.objects.get(source_object_id=meeting.pk).specific
        page.source_content_type = None
        page.source_object_id = None
        page.save()

        response = hide_inaccessible_detail_pages(page, _request(), (), {})

        assert response is not None
        assert response.status_code == NOT_FOUND

    def test_missing_source_row_returns_404(self):
        _home()
        meeting = create_meeting(peer=make_peer())
        page = MeetingDetailPage.objects.get(source_object_id=meeting.pk).specific
        page.source_object_id = 999_999
        page.save(update_fields=["source_object_id"])

        response = hide_inaccessible_detail_pages(page, _request(), (), {})

        assert response is not None
        assert response.status_code == NOT_FOUND


class TestDetailPageLifecycle:
    def test_deleting_meeting_deletes_page(self):
        _home()
        meeting = create_meeting(peer=make_peer())
        page_pk = MeetingDetailPage.objects.get(source_object_id=meeting.pk).pk

        meeting.delete()

        assert not Page.objects.filter(pk=page_pk).exists()

    def test_deleting_user_deletes_profile_page(self):
        _home()
        user = UserFactory()
        page_pk = UserProfilePage.objects.get(source_object_id=user.pk).pk

        user.delete()

        assert not Page.objects.filter(pk=page_pk).exists()


class TestAbsoluteUrlFallback:
    def test_meeting_falls_back_to_the_index(self):
        home = _home()
        index = MeetingIndexPage(title="Meetings", slug="meetings")
        home.add_child(instance=index)
        index.save_revision().publish()
        meeting = create_meeting(peer=make_peer())
        detail = MeetingDetailPage.objects.get(source_object_id=meeting.pk)

        assert meeting.get_absolute_url() == detail.get_url()

        detail.delete()

        assert meeting.get_absolute_url() == index.get_url()
