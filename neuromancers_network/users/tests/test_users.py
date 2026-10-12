from types import SimpleNamespace
from unittest.mock import patch

import pytest
from djstripe.enums import SubscriptionStatus

from neuromancers_network.users.avatar import confirm_upload
from neuromancers_network.users.forms import UserSignupForm
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

VALID_PASSWORD = "s3cret-Passw0rd!"  # noqa: S105


def signup_data(**overrides):
    data = {
        "username": "newcomer",
        "email": "newcomer@example.com",
        "email2": "newcomer@example.com",
        "password1": VALID_PASSWORD,
        "password2": VALID_PASSWORD,
        "accept_tos": True,
    }
    data.update(overrides)
    return data


def make_peer(
    *,
    is_approved=True,
    subscription_status=SubscriptionStatus.active,
    kyc_completed=True,
    is_verified=False,
):
    """Build a user wired up with the full peer lifecycle state."""
    user = UserFactory()
    PeerProfileFactory(user=user, is_approved=is_approved, is_verified=is_verified)
    payment_profile = PaymentProfileFactory(user=user, kyc_completed=kyc_completed)
    if subscription_status is not None:
        PeerSubscriptionFactory(
            payment_profile=payment_profile,
            subscription__status=subscription_status,
        )
    return user


class TestUserSignupForm:
    def test_accept_tos_is_required(self):
        form = UserSignupForm(data=signup_data(accept_tos=False))

        assert not form.is_valid()
        assert "accept_tos" in form.errors


class TestIsPeer:
    def test_unapproved_peer_profile(self):
        user = UserFactory()
        PeerProfileFactory(user=user, is_approved=False)
        assert user.is_peer is False

    def test_approved_without_payment_profile(self):
        user = UserFactory()
        PeerProfileFactory(user=user, is_approved=True)
        assert user.is_peer is False

    def test_no_peer_subscription(self):
        user = make_peer(subscription_status=None)
        assert user.is_peer is False

    @pytest.mark.parametrize(
        "status",
        [
            SubscriptionStatus.canceled,
            SubscriptionStatus.past_due,
            SubscriptionStatus.incomplete,
            SubscriptionStatus.unpaid,
            SubscriptionStatus.paused,
        ],
    )
    def test_inactive_subscription_statuses(self, status):
        user = make_peer(subscription_status=status)
        assert user.is_peer is False

    @pytest.mark.parametrize(
        "status",
        [
            SubscriptionStatus.active,
            SubscriptionStatus.trialing,
        ],
    )
    def test_active_subscription_statuses(self, status):
        user = make_peer(subscription_status=status)
        assert user.is_peer is True

    def test_kyc_incomplete(self):
        user = make_peer(kyc_completed=False)
        assert user.is_peer is False


class TestIsVerifiedPeer:
    def test_verified_but_not_peer(self):
        user = make_peer(is_verified=True, kyc_completed=False)
        assert user.is_verified_peer is False

    def test_peer_not_verified(self):
        user = make_peer(is_verified=False)
        assert user.is_peer is True
        assert user.is_verified_peer is False

    def test_verified_peer(self):
        user = make_peer(is_verified=True)
        assert user.is_peer is True
        assert user.is_verified_peer is True


class TestAvatarUpload:
    def test_confirm_stores_fields_and_deletes_previous(self):
        user = UserFactory()
        profile, _created = UserProfile.objects.get_or_create(user=user)
        profile.profile_picture_getpronto_id = "old-file"
        profile.save(update_fields=["profile_picture_getpronto_id"])
        result = SimpleNamespace(
            file={"id": "new-file", "secureUrl": "https://img.example/new"},
        )

        with (
            patch(
                "neuromancers_network.users.avatar.upload_confirm",
                return_value=result,
            ),
            patch(
                "neuromancers_network.users.avatar.delete_getpronto_file",
            ),
            patch("neuromancers_network.users.avatar.configure_getpronto"),
        ):
            url = confirm_upload(profile=profile, pending_upload_id="pending-1")

        assert url == "https://img.example/new"
        profile.refresh_from_db()
        assert profile.profile_picture_getpronto_id == "new-file"
        assert profile.profile_picture_url == "https://img.example/new"
