from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from neuromancers_network.meetings.forms_pages import ReviewFormPage
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import Review
from neuromancers_network.meetings.models import ReviewStatus
from neuromancers_network.meetings.selectors import published_reviews
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.meetings.wagtail_hooks import PublishReviewBulkAction
from neuromancers_network.meetings.wagtail_hooks import UnpublishReviewBulkAction
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _completed_request(peer=None):
    peer = peer or make_peer()
    seeker = UserFactory()
    meeting = create_meeting(peer=peer)
    request_row = MeetingRequest.objects.create(
        meeting=meeting,
        support_seeker=seeker,
        status=MeetingRequestStatus.COMPLETED,
    )
    return request_row, peer, seeker


def _review(request_row, *, status=ReviewStatus.PUBLISHED):
    return Review.objects.create(
        meeting_request=request_row,
        reviewer=request_row.support_seeker,
        peer=request_row.meeting.peer,
        rating=5,
        status=status,
    )


class TestReviewState:
    def test_is_live_is_derived_from_status(self):
        request_row, _peer, _seeker = _completed_request()

        assert _review(request_row).is_live is True
        hidden = _review(
            _completed_request()[0],
            status=ReviewStatus.HIDDEN,
        )
        assert hidden.is_live is False

    def test_published_reviews_excludes_pending_and_hidden(self):
        request_row, _peer, _seeker = _completed_request()
        _review(request_row)
        _review(
            _completed_request()[0],
            status=ReviewStatus.PENDING_APPROVAL,
        )
        _review(_completed_request()[0], status=ReviewStatus.HIDDEN)

        request = RequestFactory().get("/")
        results = published_reviews(request=request)

        assert results.count() == 1
        assert results.first().status == ReviewStatus.PUBLISHED


class TestReviewApprovalFlow:
    def _page(self, submitter):
        page = ReviewFormPage(title="Review")
        page._daisie_request = SimpleNamespace(user=submitter)  # noqa: SLF001
        return page

    def test_default_publishes_immediately(self):
        request_row, _peer, seeker = _completed_request()

        review = self._page(seeker).create_instance_from_submission(
            SimpleNamespace(
                cleaned_data={
                    "meeting_request": request_row.pk,
                    "rating": 5,
                    "comment": "Great",
                },
            ),
        )

        assert review.status == ReviewStatus.PUBLISHED

    def test_approval_policy_creates_pending(self):
        request_row, peer, seeker = _completed_request()
        profile = peer.peer_profile
        profile.reviews_require_approval = True
        profile.save(update_fields=["reviews_require_approval"])

        review = self._page(seeker).create_instance_from_submission(
            SimpleNamespace(
                cleaned_data={
                    "meeting_request": request_row.pk,
                    "rating": 5,
                    "comment": "Pending",
                },
            ),
        )

        assert review.status == ReviewStatus.PENDING_APPROVAL

    def test_peer_may_refuse_reviews(self):
        request_row, peer, seeker = _completed_request()
        profile = peer.peer_profile
        profile.accepts_reviews = False
        profile.save(update_fields=["accepts_reviews"])

        review = self._page(seeker).create_instance_from_submission(
            SimpleNamespace(
                cleaned_data={
                    "meeting_request": request_row.pk,
                    "rating": 5,
                    "comment": "No thanks",
                },
            ),
        )

        assert review is None


class TestReviewBulkActions:
    def test_publish_and_hide_are_idempotent(self):
        request_row, _peer, _seeker = _completed_request()
        review = _review(request_row, status=ReviewStatus.HIDDEN)

        PublishReviewBulkAction.execute_action([review])
        review.refresh_from_db()
        assert review.status == ReviewStatus.PUBLISHED
        PublishReviewBulkAction.execute_action([review])

        UnpublishReviewBulkAction.execute_action([review])
        review.refresh_from_db()
        assert review.status == ReviewStatus.HIDDEN
        UnpublishReviewBulkAction.execute_action([review])

        assert Review.objects.get(pk=review.pk).status == ReviewStatus.HIDDEN
