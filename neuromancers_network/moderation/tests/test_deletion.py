from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from djstripe.enums import SubscriptionStatus

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.moderation.identity import is_identity_blocked
from neuromancers_network.moderation.models import AccountDeletionRequest
from neuromancers_network.moderation.models import DeletedIdentity
from neuromancers_network.moderation.models import DeletionStatus
from neuromancers_network.moderation.services import cancel_account_deletion
from neuromancers_network.moderation.services import purge_account
from neuromancers_network.moderation.services import purge_due_accounts
from neuromancers_network.moderation.services import request_account_deletion
from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestRequestDeletion:
    def test_schedules_and_deactivates(self):
        user = UserFactory()

        deletion = request_account_deletion(user, reason="moving on")

        user.refresh_from_db()
        assert deletion.status == DeletionStatus.PENDING
        assert deletion.scheduled_for > timezone.now()
        assert user.is_active is False
        assert user.deactivated_at is not None


class TestCancelDeletion:
    def test_reactivates_and_marks_cancelled(self):
        user = UserFactory()
        request_account_deletion(user)

        cancel_account_deletion(user)

        user.refresh_from_db()
        deletion = AccountDeletionRequest.objects.get(user=user)
        assert deletion.status == DeletionStatus.CANCELLED
        assert user.is_active is True

    def test_noop_without_request(self):
        user = UserFactory()

        cancel_account_deletion(user)

        assert not AccountDeletionRequest.objects.filter(user=user).exists()


class TestPurge:
    def test_anonymises_and_records_identity(self):
        user = UserFactory()
        original_email = user.email
        original_username = user.username
        request_account_deletion(user)

        purge_account(user)

        user.refresh_from_db()
        assert user.name == ""
        assert user.username == f"deleted-{user.pk}"
        assert user.email != original_email
        assert user.is_active is False
        assert DeletedIdentity.objects.exists()
        assert is_identity_blocked(email=original_email) is True
        assert is_identity_blocked(username=original_username) is True
        assert (
            AccountDeletionRequest.objects.get(user=user).status
            == DeletionStatus.COMPLETED
        )

    def test_cancels_subscription(self):
        config = StripeSettings.load()
        config.secret_key = "sk_test_123"  # noqa: S105
        config.save()
        user = UserFactory()
        profile = PaymentProfileFactory(
            user=user,
            stripe_connect_account_id=None,
        )
        peer_subscription = PeerSubscriptionFactory(
            payment_profile=profile,
            subscription__status=SubscriptionStatus.active,
        )
        request_account_deletion(user)

        with patch(
            "neuromancers_network.payments.services.stripe.Subscription.cancel",
        ) as cancel:
            purge_account(user)

        cancel.assert_called_once_with(peer_subscription.subscription_id)

    def test_keeps_row_for_financial_records(self):
        user = UserFactory()
        user_pk = user.pk

        purge_account(user)

        assert type(user).objects.filter(pk=user_pk).exists()

    def test_purge_due_accounts_only_purges_due(self):
        due_user = UserFactory()
        later_user = UserFactory()
        request_account_deletion(due_user)
        request_account_deletion(later_user)
        AccountDeletionRequest.objects.filter(user=due_user).update(
            scheduled_for=timezone.now() - timedelta(days=1),
        )

        purged = purge_due_accounts()

        due_user.refresh_from_db()
        later_user.refresh_from_db()
        assert purged == 1
        assert due_user.username.startswith("deleted-")
        assert later_user.username != f"deleted-{later_user.pk}"


class TestIdentityBlock:
    def test_unknown_identity_is_not_blocked(self):
        assert is_identity_blocked(email="nobody@example.com") is False
