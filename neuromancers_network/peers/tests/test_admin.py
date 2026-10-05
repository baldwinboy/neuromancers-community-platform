import pytest

from neuromancers_network.peers.models import PeerApplication
from neuromancers_network.peers.models import PeerApplicationStatus
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.peers.wagtail_hooks import ApprovePeerApplicationBulkAction
from neuromancers_network.peers.wagtail_hooks import RejectPeerApplicationBulkAction
from neuromancers_network.peers.wagtail_hooks import UnverifyPeerBulkAction
from neuromancers_network.peers.wagtail_hooks import VerifyPeerBulkAction
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestPeerApplicationActions:
    def test_approve_marks_application_and_profile(self):
        applicant = UserFactory()
        application = PeerApplication.objects.create(user=applicant, reason="Why")
        reviewer = UserFactory()

        ApprovePeerApplicationBulkAction.execute_action(
            [application],
            reviewer=reviewer,
        )

        application.refresh_from_db()
        applicant.peer_profile.refresh_from_db()
        assert application.status == PeerApplicationStatus.APPROVED
        assert application.reviewed_by == reviewer
        assert applicant.peer_profile.is_approved is True

    def test_reject_marks_application(self):
        applicant = UserFactory()
        application = PeerApplication.objects.create(user=applicant, reason="Why")
        reviewer = UserFactory()

        RejectPeerApplicationBulkAction.execute_action(
            [application],
            reviewer=reviewer,
        )

        application.refresh_from_db()
        assert application.status == PeerApplicationStatus.REJECTED
        assert application.reviewed_by == reviewer


class TestPeerVerificationActions:
    def test_verify_sets_flags(self):
        profile = make_peer().peer_profile
        reviewer = UserFactory()

        VerifyPeerBulkAction.execute_action([profile], reviewer=reviewer)

        profile.refresh_from_db()
        assert profile.is_verified is True
        assert profile.verified_by == reviewer

    def test_unverify_clears_flags(self):
        profile = make_peer(is_verified=True).peer_profile
        reviewer = UserFactory()

        UnverifyPeerBulkAction.execute_action([profile], reviewer=reviewer)

        profile.refresh_from_db()
        assert profile.is_verified is False
        assert profile.verified_by == reviewer
