import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from djstripe.enums import SubscriptionStatus

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.moderation.identity import is_identity_blocked
from neuromancers_network.moderation.identity import sweep_deleted_identities
from neuromancers_network.moderation.models import AccountDeletionRequest
from neuromancers_network.moderation.models import DeletedIdentity
from neuromancers_network.moderation.models import DeletionStatus
from neuromancers_network.moderation.services import cancel_account_deletion
from neuromancers_network.moderation.services import purge_account
from neuromancers_network.moderation.services import purge_due_accounts
from neuromancers_network.moderation.services import request_account_deletion
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.models.choices import StaffState
from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


SUCCESS = 200
GONE = 410


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

    def test_scrubs_residual_identity_and_privilege(self):
        moderator = UserFactory(staff_state=StaffState.ACTIVE)
        user = UserFactory(
            staff_state=StaffState.ACTIVE,
            deactivation_reason="personal",
        )
        user.username_changed_at = timezone.now()
        user.email_changed_at = timezone.now()
        user.save(update_fields=["username_changed_at", "email_changed_at"])
        UserProfile.objects.update_or_create(
            user=user,
            defaults={"access_needs": "needs", "bio": "member bio"},
        )
        peer_profile = PeerProfileFactory(user=user)
        peer_profile.is_approved = True
        peer_profile.approved_by = moderator
        peer_profile.approved_at = timezone.now()
        peer_profile.is_verified = True
        peer_profile.verified_by = moderator
        peer_profile.verified_at = timezone.now()
        peer_profile.provider_agreement_accepted_at = timezone.now()
        peer_profile.provider_agreement_version = "1"
        peer_profile.default_terms = "terms"
        peer_profile.terms_templates = [{"name": "Template", "body": "Body"}]
        peer_profile.save()
        payment_profile = PaymentProfileFactory(
            user=user,
            stripe_connect_account_id=None,
        )
        customer = payment_profile.stripe_customer_id
        customer.email = "pii@example.com"
        customer.stripe_data = {
            **(customer.stripe_data or {}),
            "name": "PII Name",
            "address": {"line1": "1 Road"},
        }
        customer.save()
        request_account_deletion(user)

        purge_account(user)

        user.refresh_from_db()
        peer_profile.refresh_from_db()
        payment_profile.refresh_from_db()
        customer.refresh_from_db()
        assert user.deactivation_reason == ""
        assert user.username_changed_at is None
        assert user.email_changed_at is None
        assert user.is_superuser is False
        assert user.is_staff is False
        assert peer_profile.terms_templates == []
        assert peer_profile.provider_agreement_accepted_at is None
        assert peer_profile.provider_agreement_version == ""
        assert peer_profile.is_approved is False
        assert peer_profile.approved_by is None
        assert peer_profile.is_verified is False
        assert peer_profile.verified_by is None
        assert payment_profile.kyc_completed is False
        assert customer.email == ""
        assert "name" not in customer.stripe_data
        assert "address" not in customer.stripe_data

    def test_purge_is_idempotent(self):
        user = UserFactory()

        purge_account(user)
        purge_account(user)

        assert DeletedIdentity.objects.count() == 1

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


class TestPurgeDueAccountsIsolation:
    def test_failure_for_one_user_does_not_block_the_rest(self, caplog):
        failing_user = UserFactory()
        healthy_user = UserFactory()
        request_account_deletion(failing_user)
        request_account_deletion(healthy_user)
        AccountDeletionRequest.objects.filter(
            user__in=[failing_user, healthy_user],
        ).update(scheduled_for=timezone.now() - timedelta(days=1))

        real_purge_account = purge_account

        def flaky_purge(user):
            if user.pk == failing_user.pk:
                message = "stripe unavailable"
                raise RuntimeError(message)
            real_purge_account(user)

        with (
            patch(
                "neuromancers_network.moderation.services.purge_account",
                side_effect=flaky_purge,
            ),
            caplog.at_level(
                logging.ERROR,
                logger="neuromancers_network.moderation.services",
            ),
        ):
            purged = purge_due_accounts()

        healthy_user.refresh_from_db()
        failed_deletion = AccountDeletionRequest.objects.get(user=failing_user)
        assert purged == 1
        assert healthy_user.username == f"deleted-{healthy_user.pk}"
        assert failed_deletion.status == DeletionStatus.PENDING
        assert "Failed to purge account deletion" in caplog.text
        assert str(failing_user.pk) in caplog.text


class TestDeletedIdentitySweep:
    def test_deletes_only_expired_identities(self):
        expired = DeletedIdentity.objects.create(
            email_hash="expired-email",
            username_hash="expired-user",
            purge_after=timezone.now() - timedelta(days=1),
        )
        retained = DeletedIdentity.objects.create(
            email_hash="retained-email",
            username_hash="retained-user",
            purge_after=timezone.now() + timedelta(days=1),
        )

        deleted = sweep_deleted_identities()

        assert deleted == 1
        assert not DeletedIdentity.objects.filter(pk=expired.pk).exists()
        assert DeletedIdentity.objects.filter(pk=retained.pk).exists()

    def test_sweep_is_idempotent(self):
        DeletedIdentity.objects.create(
            email_hash="expired-email",
            username_hash="expired-user",
            purge_after=timezone.now() - timedelta(days=1),
        )

        assert sweep_deleted_identities() == 1
        assert sweep_deleted_identities() == 0


class TestIdentityBlock:
    def test_unknown_identity_is_not_blocked(self):
        assert is_identity_blocked(email="nobody@example.com") is False


class TestDeletionCancelLink:
    def _deletion(self):
        user = UserFactory()
        deletion = request_account_deletion(user)
        return user, deletion

    def test_valid_get_does_not_cancel(self, client):
        from django.urls import reverse  # noqa: PLC0415

        from neuromancers_network.moderation.tokens import deletion_cancel_token  # noqa: PLC0415

        user, deletion = self._deletion()
        token = deletion_cancel_token(deletion)

        response = client.get(
            reverse("account_deletion_cancel", args=[token]),
        )

        assert response.status_code == SUCCESS
        deletion.refresh_from_db()
        user.refresh_from_db()
        assert deletion.status == DeletionStatus.PENDING
        assert user.is_active is False

    def test_post_cancels_and_reactivates(self, client):
        from django.urls import reverse  # noqa: PLC0415

        from neuromancers_network.moderation.tokens import deletion_cancel_token  # noqa: PLC0415

        user, deletion = self._deletion()
        token = deletion_cancel_token(deletion)

        response = client.post(
            reverse("account_deletion_cancel", args=[token]),
        )

        assert response.status_code == SUCCESS
        deletion.refresh_from_db()
        user.refresh_from_db()
        assert deletion.status == DeletionStatus.CANCELLED
        assert user.is_active is True

    def test_token_is_one_time(self, client):
        from django.urls import reverse  # noqa: PLC0415

        from neuromancers_network.moderation.tokens import deletion_cancel_token  # noqa: PLC0415

        _user, deletion = self._deletion()
        token = deletion_cancel_token(deletion)
        url = reverse("account_deletion_cancel", args=[token])

        assert client.post(url).status_code == SUCCESS
        assert client.post(url).status_code == GONE

    def test_tampered_token_is_rejected(self, client):
        from django.urls import reverse  # noqa: PLC0415

        _user, _deletion = self._deletion()
        url = reverse("account_deletion_cancel", args=["not-a-token"])

        assert client.get(url).status_code == GONE
        assert client.post(url).status_code == GONE
