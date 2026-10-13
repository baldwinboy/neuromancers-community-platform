from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from django.utils import timezone
from djstripe.enums import SubscriptionStatus
from wagtail.models import Page

from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models.pages import MeetingDetailPage
from neuromancers_network.core.models.pages import MeetingIndexPage
from neuromancers_network.core.wagtail_hooks import hide_inaccessible_detail_pages
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import Review
from neuromancers_network.meetings.selectors import published_meetings
from neuromancers_network.meetings.selectors import published_reviews
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.moderation.models import UserBlock
from neuromancers_network.moderation.visibility import hidden_user_ids
from neuromancers_network.moderation.visibility import source_is_public
from neuromancers_network.moderation.visibility import source_owner
from neuromancers_network.moderation.visibility import viewer_can_view_source
from neuromancers_network.peers.selectors import approved_peers
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.models.choices import ProfileVisibility
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

HTTP_NOT_FOUND = 404


def _request(user=None, **params):
    request = RequestFactory().get("/", params)
    request.user = user if user is not None else AnonymousUser()
    return request


class TestHiddenUserIds:
    def test_anonymous_has_none(self):
        assert hidden_user_ids(AnonymousUser()) == set()

    def test_symmetric_both_directions(self):
        viewer = UserFactory()
        blocked = UserFactory()
        blocker = UserFactory()
        UserBlock.objects.create(blocker=viewer, blocked=blocked)
        UserBlock.objects.create(blocker=blocker, blocked=viewer)

        assert hidden_user_ids(viewer) == {blocked.pk, blocker.pk}


class TestSourceOwner:
    def test_user_is_own_owner(self):
        user = UserFactory()
        assert source_owner(user) == user

    def test_peer_profile_owner_is_user(self):
        peer = make_peer()
        assert source_owner(peer.peer_profile) == peer

    def test_meeting_owner_is_peer(self):
        peer = make_peer()
        meeting = create_meeting(peer=peer)
        assert source_owner(meeting) == peer


class TestMeetingVisibility:
    def test_published_meeting_visible_to_anonymous(self):
        meeting = create_meeting(peer=make_peer())
        assert source_is_public(meeting) is True
        assert viewer_can_view_source(meeting, AnonymousUser()) is True

    def test_unpublished_meeting_hidden(self):
        meeting = create_meeting(peer=make_peer(), status=MeetingStatus.DRAFT)
        assert source_is_public(meeting) is False
        assert viewer_can_view_source(meeting, UserFactory()) is False

    def test_paused_plan_owner_hidden(self):
        peer = make_peer(subscription_status=SubscriptionStatus.paused)
        meeting = create_meeting(peer=peer)
        assert viewer_can_view_source(meeting, UserFactory()) is False

    def test_owner_still_sees_paused_own_page(self):
        peer = make_peer(subscription_status=SubscriptionStatus.paused)
        meeting = create_meeting(peer=peer)
        assert viewer_can_view_source(meeting, peer) is True

    def test_moderator_sees_hidden_page(self):
        peer = make_peer(subscription_status=SubscriptionStatus.paused)
        meeting = create_meeting(peer=peer)
        moderator = UserFactory(is_superuser=True)
        assert viewer_can_view_source(meeting, moderator) is True

    def test_blocked_owner_hidden(self):
        peer = make_peer()
        meeting = create_meeting(peer=peer)
        viewer = UserFactory()
        UserBlock.objects.create(blocker=viewer, blocked=peer)
        assert viewer_can_view_source(meeting, viewer) is False


class TestUserProfileVisibility:
    def _user_with_visibility(self, visibility):
        user = UserFactory()
        UserProfile.objects.update_or_create(
            user=user,
            defaults={"visibility": visibility},
        )
        return user

    def test_public_profile_visible_to_anonymous(self):
        owner = self._user_with_visibility(ProfileVisibility.PUBLIC)
        assert viewer_can_view_source(owner, AnonymousUser()) is True

    def test_members_profile_hidden_from_anonymous(self):
        owner = self._user_with_visibility(ProfileVisibility.MEMBERS)
        assert viewer_can_view_source(owner, AnonymousUser()) is False

    def test_members_profile_visible_to_member(self):
        owner = self._user_with_visibility(ProfileVisibility.MEMBERS)
        assert viewer_can_view_source(owner, UserFactory()) is True

    def test_private_profile_hidden_from_others(self):
        owner = self._user_with_visibility(ProfileVisibility.PRIVATE)
        assert viewer_can_view_source(owner, UserFactory()) is False

    def test_private_profile_visible_to_owner(self):
        owner = self._user_with_visibility(ProfileVisibility.PRIVATE)
        assert viewer_can_view_source(owner, owner) is True

    def test_deactivated_owner_hidden(self):
        owner = self._user_with_visibility(ProfileVisibility.PUBLIC)
        owner.is_active = False
        owner.deactivated_at = timezone.now()
        owner.save(update_fields=["is_active", "deactivated_at"])
        assert viewer_can_view_source(owner, UserFactory()) is False


class TestFeedParity:
    def test_published_meetings_excludes_blocked_peer(self):
        peer = make_peer()
        create_meeting(peer=peer)
        viewer = UserFactory()
        UserBlock.objects.create(blocker=viewer, blocked=peer)

        assert not published_meetings(request=_request(viewer)).exists()

    def test_published_meetings_excludes_peer_who_blocked_viewer(self):
        peer = make_peer()
        create_meeting(peer=peer)
        viewer = UserFactory()
        UserBlock.objects.create(blocker=peer, blocked=viewer)

        assert not published_meetings(request=_request(viewer)).exists()

    def test_published_meetings_excludes_paused_peer(self):
        peer = make_peer(subscription_status=SubscriptionStatus.paused)
        create_meeting(peer=peer)

        assert not published_meetings(request=_request()).exists()

    def test_approved_peers_excludes_blocked(self):
        peer = make_peer()
        viewer = UserFactory()
        UserBlock.objects.create(blocker=viewer, blocked=peer)

        assert not approved_peers(request=_request(viewer)).exists()

    def test_published_reviews_excludes_blocked_reviewer(self):
        reviewed = make_peer()
        reviewer = make_peer()
        meeting = create_meeting(peer=reviewed)
        booking = create_booking(
            meeting=meeting,
            seeker=reviewer,
            sessions=[{"requested_duration_minutes": 30}],
        )
        Review.objects.create(
            meeting_request=booking.sessions.first(),
            reviewer=reviewer,
            peer=reviewed,
            rating=5,
            is_published=True,
        )
        viewer = UserFactory()
        UserBlock.objects.create(blocker=viewer, blocked=reviewer)

        assert not published_reviews(request=_request(viewer)).exists()


def _detail_page(meeting):
    """Return a live detail page bound to *meeting* (bridge-created or manual)."""
    existing = MeetingDetailPage.objects.filter(source_object_id=meeting.pk).first()
    if existing is not None:
        return existing.specific

    root = Page.get_first_root_node()
    home = HomePage.objects.first() or HomePage(title="Home", slug="home")
    if home.pk is None:
        root.add_child(instance=home)
    index = MeetingIndexPage.objects.first() or MeetingIndexPage(
        title="Meetings",
        slug="meetings",
    )
    if index.pk is None:
        home.add_child(instance=index)
    page = MeetingDetailPage(
        title=meeting.title,
        slug=f"meeting-{meeting.pk}",
        detail_key="meeting",
        source_content_type=ContentType.objects.get_for_model(Meeting),
        source_object_id=meeting.pk,
    )
    index.add_child(instance=page)
    page.save_revision().publish()
    return page.specific


class TestServeHook:
    def test_public_meeting_served(self):
        meeting = create_meeting(peer=make_peer())
        page = _detail_page(meeting)

        assert hide_inaccessible_detail_pages(page, _request(), (), {}) is None

    def test_paused_plan_owner_gets_404(self):
        peer = make_peer(subscription_status=SubscriptionStatus.paused)
        meeting = create_meeting(peer=peer)
        page = _detail_page(meeting)

        response = hide_inaccessible_detail_pages(page, _request(UserFactory()), (), {})
        assert response is not None
        assert response.status_code == HTTP_NOT_FOUND

    def test_owner_bypasses_hook(self):
        peer = make_peer(subscription_status=SubscriptionStatus.paused)
        meeting = create_meeting(peer=peer)
        page = _detail_page(meeting)

        assert hide_inaccessible_detail_pages(page, _request(peer), (), {}) is None

    def test_blocked_viewer_gets_404(self):
        peer = make_peer()
        meeting = create_meeting(peer=peer)
        page = _detail_page(meeting)
        viewer = UserFactory()
        UserBlock.objects.create(blocker=viewer, blocked=peer)

        response = hide_inaccessible_detail_pages(page, _request(viewer), (), {})
        assert response is not None
        assert response.status_code == HTTP_NOT_FOUND

    def test_non_detail_page_untouched(self):
        home = HomePage.objects.first()
        if home is None:
            root = Page.get_first_root_node()
            home = HomePage(title="Home", slug="home")
            root.add_child(instance=home)

        assert hide_inaccessible_detail_pages(home, _request(), (), {}) is None
