import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from djstripe.enums import SubscriptionStatus

from neuromancers_network.core.models import AccountAuditLog
from neuromancers_network.core.models import CalendarFeedToken
from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.services import is_eligible_peer
from neuromancers_network.users.actions import account_deactivate
from neuromancers_network.users.actions import account_reactivate
from neuromancers_network.users.services import deactivate_account
from neuromancers_network.users.services import reactivate_account
from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def make_eligible_peer():
    user = UserFactory()
    PeerProfileFactory(user=user, is_approved=True)
    profile = PaymentProfileFactory(user=user, kyc_completed=True)
    PeerSubscriptionFactory(
        payment_profile=profile,
        subscription__status=SubscriptionStatus.active,
    )
    return user


def _request(user):
    request = RequestFactory().post("/")
    request.user = user
    return request


class TestDeactivateAccount:
    def test_sets_flags_and_withdraws_content(self):
        peer = make_eligible_peer()
        meeting = create_meeting(peer, status=MeetingStatus.PUBLISHED)
        CalendarFeedToken.objects.create(user=peer)

        deactivate_account(peer, reason="taking a break")

        peer.refresh_from_db()
        meeting.refresh_from_db()
        assert peer.is_active is False
        assert peer.deactivated_at is not None
        assert peer.deactivation_reason == "taking a break"
        assert meeting.status == MeetingStatus.DRAFT
        assert peer.calendar_feed_token.is_active is False

    def test_emits_event_and_audit(self):
        peer = make_eligible_peer()

        deactivate_account(peer)

        assert NotificationEventLog.objects.filter(
            event_type="account_deactivated",
        ).exists()
        assert AccountAuditLog.objects.filter(action="account.deactivate").exists()

    def test_is_idempotent(self):
        peer = make_eligible_peer()

        deactivate_account(peer)
        stamp = peer.deactivated_at
        deactivate_account(peer)

        peer.refresh_from_db()
        assert peer.deactivated_at == stamp

    def test_deactivated_peer_is_not_eligible(self):
        peer = make_eligible_peer()
        assert is_eligible_peer(peer) is True

        deactivate_account(peer)
        peer.refresh_from_db()

        assert is_eligible_peer(peer) is False


class TestReactivateAccount:
    def test_restores_access_and_token(self):
        peer = make_eligible_peer()
        token = CalendarFeedToken.objects.create(user=peer)
        deactivate_account(peer, reason="break")

        reactivate_account(peer)

        peer.refresh_from_db()
        token.refresh_from_db()
        assert peer.is_active is True
        assert peer.deactivated_at is None
        assert peer.deactivation_reason == ""
        assert token.is_active is True
        assert NotificationEventLog.objects.filter(
            event_type="account_reactivated",
        ).exists()

    def test_does_not_republish_meetings(self):
        peer = make_eligible_peer()
        meeting = create_meeting(peer, status=MeetingStatus.PUBLISHED)
        deactivate_account(peer)

        reactivate_account(peer)

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.DRAFT


class TestLifecycleActions:
    def test_self_deactivation(self):
        user = UserFactory()

        account_deactivate(_request(user), {"reason": "done"})

        user.refresh_from_db()
        assert user.is_active is False

    def test_non_moderator_cannot_target_other(self):
        actor = UserFactory()
        other = UserFactory()

        with pytest.raises(PermissionDenied):
            account_deactivate(_request(actor), {"user": other.pk})

        other.refresh_from_db()
        assert other.is_active is True

    def test_moderator_can_target_other_and_reactivate(self):
        actor = UserFactory(is_superuser=True)
        other = UserFactory()

        account_deactivate(_request(actor), {"user": other.pk})
        other.refresh_from_db()
        assert other.is_active is False

        account_reactivate(_request(actor), {"user": other.pk})
        other.refresh_from_db()
        assert other.is_active is True
