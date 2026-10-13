from datetime import timedelta
from types import SimpleNamespace

import pytest
from allauth.account.signals import email_changed
from django.core.exceptions import ValidationError
from django.utils import timezone

from neuromancers_network.core.models import AccountAuditLog
from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.users.cooldown import cooldown_remaining
from neuromancers_network.users.cooldown import ensure_email_change_allowed
from neuromancers_network.users.cooldown import ensure_username_change_allowed
from neuromancers_network.users.forms import AddEmailForm
from neuromancers_network.users.settings import AccountForm
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestCooldownRemaining:
    def test_none_last_changed(self):
        assert cooldown_remaining(None, 30) is None

    def test_zero_days_disables(self):
        assert cooldown_remaining(timezone.now(), 0) is None

    def test_recent_change_is_active(self):
        remaining = cooldown_remaining(timezone.now(), 30)

        assert remaining is not None
        assert remaining > timedelta(0)

    def test_elapsed_change_is_inactive(self):
        old = timezone.now() - timedelta(days=40)

        assert cooldown_remaining(old, 30) is None


class TestEnsureUsernameChangeAllowed:
    def test_first_change_allowed(self):
        ensure_username_change_allowed(UserFactory())

    def test_recent_change_blocked(self):
        user = UserFactory(username_changed_at=timezone.now())

        with pytest.raises(ValidationError) as exc:
            ensure_username_change_allowed(user)

        assert exc.value.code == "username_cooldown"

    def test_elapsed_change_allowed(self):
        user = UserFactory(username_changed_at=timezone.now() - timedelta(days=40))

        ensure_username_change_allowed(user)

    def test_moderator_bypasses(self):
        user = UserFactory(
            is_superuser=True,
            username_changed_at=timezone.now(),
        )

        ensure_username_change_allowed(user)


class TestEnsureEmailChangeAllowed:
    def test_recent_change_blocked(self):
        user = UserFactory(email_changed_at=timezone.now())

        with pytest.raises(ValidationError) as exc:
            ensure_email_change_allowed(user)

        assert exc.value.code == "email_cooldown"

    def test_elapsed_change_allowed(self):
        user = UserFactory(email_changed_at=timezone.now() - timedelta(days=40))

        ensure_email_change_allowed(user)


class TestAccountForm:
    def _data(self, username):
        return {"name": "Name", "username": username, "date_of_birth": ""}

    def test_change_blocked_during_cooldown(self):
        user = UserFactory(username_changed_at=timezone.now())

        form = AccountForm(self._data("newname"), instance=user)

        assert not form.is_valid()
        assert "username" in form.errors

    def test_first_change_records_event_and_audit(self):
        user = UserFactory(username="oldname")

        form = AccountForm(self._data("newname"), instance=user)
        assert form.is_valid()
        form.save()

        user.refresh_from_db()
        assert user.username == "newname"
        assert user.username_changed_at is not None
        assert NotificationEventLog.objects.filter(
            event_type="username_changed",
        ).exists()
        assert AccountAuditLog.objects.filter(action="account.username_change").exists()

    def test_unchanged_username_does_not_stamp(self):
        user = UserFactory(username="samename")

        form = AccountForm(self._data("samename"), instance=user)
        assert form.is_valid()
        form.save()

        user.refresh_from_db()
        assert user.username_changed_at is None
        assert not NotificationEventLog.objects.filter(
            event_type="username_changed",
        ).exists()


class TestAddEmailForm:
    def test_add_blocked_during_cooldown(self):
        user = UserFactory(email_changed_at=timezone.now())

        form = AddEmailForm(user=user, data={"email": "new@example.com"})

        assert not form.is_valid()
        assert "email" in form.errors

    def test_add_allowed_after_cooldown(self):
        user = UserFactory(email_changed_at=timezone.now() - timedelta(days=40))

        form = AddEmailForm(user=user, data={"email": "new@example.com"})

        assert form.is_valid()


class TestEmailChangedSignal:
    def test_signal_stamps_and_records(self):
        user = UserFactory()
        previous = SimpleNamespace(email="old@example.com")
        current = SimpleNamespace(email="new@example.com")

        email_changed.send(
            sender=None,
            request=None,
            user=user,
            from_email_address=previous,
            to_email_address=current,
        )

        user.refresh_from_db()
        assert user.email_changed_at is not None
        assert NotificationEventLog.objects.filter(event_type="email_changed").exists()
        assert AccountAuditLog.objects.filter(action="account.email_change").exists()

    def test_first_email_is_not_treated_as_change(self):
        user = UserFactory()

        email_changed.send(
            sender=None,
            request=None,
            user=user,
            from_email_address=None,
        )

        user.refresh_from_db()
        assert user.email_changed_at is None
        assert not NotificationEventLog.objects.filter(
            event_type="email_changed",
        ).exists()
