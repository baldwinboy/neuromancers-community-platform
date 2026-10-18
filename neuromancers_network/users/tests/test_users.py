from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.apps import apps
from django.contrib.sessions.middleware import SessionMiddleware
from django.db.models.signals import post_save
from django.test import RequestFactory
from djstripe.enums import SubscriptionStatus

from neuromancers_network.inbox.models import Notification
from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.moderation.models import EmailBan
from neuromancers_network.users.avatar import confirm_upload
from neuromancers_network.users.forms import UserCreationForm
from neuromancers_network.users.forms import UserEditForm
from neuromancers_network.users.forms import UserSignupForm
from neuromancers_network.users.models import User
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

VALID_PASSWORD = "s3cret-Passw0rd!"  # noqa: S105
BIRTH_DATE = "1990-01-02"


def signup_data(**overrides):
    data = {
        "username": "newcomer",
        "email": "newcomer@example.com",
        "email2": "newcomer@example.com",
        "password1": VALID_PASSWORD,
        "password2": VALID_PASSWORD,
        "name": "New Comer",
        "date_of_birth": BIRTH_DATE,
        "accepted_tos": True,
    }
    data.update(overrides)
    return data


def signup_request():
    """A request carrying a session (allauth's signup save reads it)."""
    request = RequestFactory().get("/")
    SessionMiddleware(lambda r: None).process_request(request)
    return request


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
    def test_accepted_tos_is_required(self):
        form = UserSignupForm(data=signup_data(accepted_tos=False))

        assert not form.is_valid()
        assert "accepted_tos" in form.errors

    def test_name_and_date_of_birth_are_required(self):
        form = UserSignupForm(data=signup_data(name="", date_of_birth=""))

        assert not form.is_valid()
        assert "name" in form.errors
        assert "date_of_birth" in form.errors

    def test_save_persists_profile_fields(self):
        form = UserSignupForm(data=signup_data())
        assert form.is_valid(), form.errors

        user = form.save(signup_request())

        assert user.name == "New Comer"
        assert user.date_of_birth.isoformat() == BIRTH_DATE
        assert user.accepted_tos is True


class TestUserSignupQuarantine:
    def test_banned_signup_is_inactive_before_creation_event(self):
        EmailBan.objects.create(value="banned@example.com")
        created_states = []

        def capture(sender, instance, created, **kwargs):
            if created:
                created_states.append(instance.is_active)

        post_save.connect(
            capture,
            sender=User,
            weak=False,
            dispatch_uid="users.tests.quarantine_state",
        )
        try:
            form = UserSignupForm(
                data=signup_data(
                    email="banned@example.com",
                    email2="banned@example.com",
                ),
            )
            assert form.is_valid(), form.errors
            user = form.save(signup_request())
        finally:
            post_save.disconnect(
                sender=User,
                dispatch_uid="users.tests.quarantine_state",
            )

        user.refresh_from_db()
        assert user.is_active is False
        assert created_states == [False]


class TestGetFullName:
    def test_returns_name(self):
        assert UserFactory(name="Ada Lovelace").get_full_name() == "Ada Lovelace"

    def test_blank_when_name_empty(self):
        assert UserFactory(name="").get_full_name() == ""


class TestAdminUserForms:
    def test_custom_app_config_registers_project_viewset(self):
        config = apps.get_app_config("wagtailusers")
        assert config.user_viewset == "neuromancers_network.users.viewsets.UserViewSet"

    @pytest.mark.parametrize("form_class", [UserCreationForm, UserEditForm])
    def test_forms_use_name_not_first_last(self, form_class):
        form = form_class()

        assert "name" in form.fields
        assert "date_of_birth" in form.fields
        assert "first_name" not in form.fields
        assert "last_name" not in form.fields

    def test_edit_form_saves_name_and_date_of_birth(self):
        user = UserFactory(name="Old Name")
        form = UserEditForm(
            data={
                "username": user.username,
                "email": user.email,
                "name": "Grace Hopper",
                "date_of_birth": "1906-12-09",
                "is_active": True,
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

        form.save()
        user.refresh_from_db()
        assert user.name == "Grace Hopper"
        assert user.date_of_birth.isoformat() == "1906-12-09"


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


class TestAvatarUploadTimeout:
    def test_put_bytes_sets_upload_timeout(self):
        from neuromancers_network.users.avatar import (  # noqa: PLC0415
            UPLOAD_TIMEOUT_SECONDS,
        )
        from neuromancers_network.users.avatar import _put_bytes  # noqa: PLC0415

        file = SimpleNamespace(seek=lambda _pos: None, read=lambda: b"bytes")
        with patch(
            "neuromancers_network.users.avatar.urllib.request.urlopen",
        ) as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b""
            _put_bytes("https://upload.example/object", file, "image/png")

        _args, kwargs = urlopen.call_args
        assert kwargs["timeout"] == UPLOAD_TIMEOUT_SECONDS


class TestAccountDeletedEvent:
    def test_delete_emits_event_without_in_app_notification(self):
        user = UserFactory()
        user_pk = user.pk

        user.delete()

        log = NotificationEventLog.objects.get(
            event_type="account_deleted",
            event_ref=f"user.{user_pk}.deleted",
        )
        assert log.payload["skip_in_app"] is True
        assert log.payload["recipient_user_ids"] == [user_pk]
        assert not Notification.objects.filter(recipient_id=user_pk).exists()
