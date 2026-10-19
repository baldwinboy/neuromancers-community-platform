from __future__ import annotations

from itertools import count

import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from neuromancers_network.core.models import AccountAuditLog
from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.meetings.actions import review_approve
from neuromancers_network.meetings.actions import review_hide
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import Review
from neuromancers_network.meetings.models import ReviewStatus
from neuromancers_network.meetings.selectors import my_hidden_reviews
from neuromancers_network.meetings.selectors import my_pending_reviews
from neuromancers_network.meetings.selectors import my_published_reviews
from neuromancers_network.meetings.selectors import review_stats
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.moderation.models import UserBlock
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

_MEETING_SEQUENCE = count(1)


def _request(user):
    request = RequestFactory().post("/")
    request.user = user
    return request


def _completed_request(peer=None, seeker=None):
    peer = peer or make_peer()
    seeker = seeker or UserFactory()
    meeting = create_meeting(
        peer=peer,
        title=f"Review meeting {next(_MEETING_SEQUENCE)}",
    )
    request_row = MeetingRequest.objects.create(
        meeting=meeting,
        support_seeker=seeker,
        status=MeetingRequestStatus.COMPLETED,
    )
    return request_row, peer, seeker


def _review(request_row, *, status=ReviewStatus.PENDING_APPROVAL):
    return Review.objects.create(
        meeting_request=request_row,
        reviewer=request_row.support_seeker,
        peer=request_row.meeting.peer,
        rating=5,
        comment="Well held",
        status=status,
    )


class TestPeerReviewActions:
    def test_peer_approves_pending_review(self):
        request_row, peer, seeker = _completed_request()
        review = _review(request_row)

        review_approve(_request(peer), {"review": review.pk})

        review.refresh_from_db()
        assert review.status == ReviewStatus.PUBLISHED
        assert AccountAuditLog.objects.filter(
            action="review.peer_approve",
            actor=peer,
            user=seeker,
        ).exists()
        assert NotificationEventLog.objects.filter(
            event_type="review_published",
            event_ref=f"review.{review.pk}.published",
        ).exists()

    def test_peer_hides_review_and_it_is_idempotent(self):
        request_row, peer, seeker = _completed_request()
        review = _review(request_row, status=ReviewStatus.PUBLISHED)

        review_hide(_request(peer), {"review": review.pk})
        review_hide(_request(peer), {"review": review.pk})

        review.refresh_from_db()
        assert review.status == ReviewStatus.HIDDEN
        assert (
            AccountAuditLog.objects.filter(
                action="review.peer_hide",
                actor=peer,
                user=seeker,
            ).count()
            == 1
        )
        assert NotificationEventLog.objects.filter(
            event_type="review_hidden",
            event_ref=f"review.{review.pk}.hidden",
        ).exists()

    def test_hidden_review_cannot_be_approved(self):
        request_row, peer, _seeker = _completed_request()
        review = _review(request_row, status=ReviewStatus.HIDDEN)

        with pytest.raises(PermissionDenied, match="hidden review"):
            review_approve(_request(peer), {"review": review.pk})

    def test_other_peer_cannot_manage_the_review(self):
        request_row, _peer, _seeker = _completed_request()
        review = _review(request_row)

        with pytest.raises(PermissionDenied, match="not found"):
            review_hide(_request(make_peer()), {"review": review.pk})

    def test_pending_creation_notifies_the_peer(self):
        request_row, _peer, _seeker = _completed_request()

        review = _review(request_row)

        assert NotificationEventLog.objects.filter(
            event_type="review_pending_approval",
            event_ref=f"review.{review.pk}.pending_approval",
        ).exists()


class TestReviewStats:
    def test_only_published_reviews_count(self):
        rating = 5

        request_row, peer, seeker = _completed_request()
        _review(request_row, status=ReviewStatus.PUBLISHED)
        _review(
            _completed_request(peer=peer, seeker=seeker)[0],
            status=ReviewStatus.PENDING_APPROVAL,
        )

        stats = review_stats(peer)

        assert stats["rating"] == rating
        assert stats["rating_count"] == 1
        assert stats["review_count"] == 1

    def test_preferences_gate_public_fields(self):
        request_row, peer, _seeker = _completed_request()
        _review(request_row, status=ReviewStatus.PUBLISHED)
        profile = peer.peer_profile
        profile.show_review_rating = False
        profile.show_rating_count = False
        profile.show_sessions_count = False
        profile.save(
            update_fields=[
                "show_review_rating",
                "show_rating_count",
                "show_sessions_count",
            ],
        )

        stats = review_stats(peer)

        assert stats["rating"] is None
        assert stats["rating_count"] is None
        assert stats["sessions"] is None

    def test_blocked_reviewer_is_excluded(self):
        request_row, peer, seeker = _completed_request()
        _review(request_row, status=ReviewStatus.PUBLISHED)
        viewer = UserFactory()
        UserBlock.objects.create(blocker=viewer, blocked=seeker)

        stats = review_stats(peer, viewer=viewer)

        assert stats["rating_count"] == 0


class TestPeerReviewLists:
    def test_status_lists_are_scoped_to_the_peer(self):
        request_row, peer, seeker = _completed_request()
        pending = _review(request_row)
        published = _review(
            _completed_request(peer=peer, seeker=seeker)[0],
            status=ReviewStatus.PUBLISHED,
        )
        hidden = _review(
            _completed_request(peer=peer, seeker=seeker)[0],
            status=ReviewStatus.HIDDEN,
        )
        request = RequestFactory().get("/")
        request.user = peer

        assert list(my_pending_reviews(request)) == [pending]
        assert list(my_published_reviews(request)) == [published]
        assert list(my_hidden_reviews(request)) == [hidden]
