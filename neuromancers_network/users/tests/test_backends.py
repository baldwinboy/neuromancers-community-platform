from __future__ import annotations

import pytest
from django.contrib.auth import authenticate
from django.utils import timezone

from neuromancers_network.users.backends import SigninGuardAllauthBackend
from neuromancers_network.users.backends import SigninGuardModelBackend
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

HTTP_OK = 200
HTTP_FORBIDDEN = 403
_LOGIN_VALUE = "correct-horse-battery-staple"
SETTINGS_URL = "/settings/forms/settings.account/"


class TestSigninGuardBackends:
    def test_model_backend_restores_active_user(self):
        user = UserFactory()
        assert SigninGuardModelBackend().get_user(user.pk) == user

    def test_allauth_backend_restores_active_user(self):
        user = UserFactory()
        assert SigninGuardAllauthBackend().get_user(user.pk) == user

    def test_model_backend_drops_inactive_user(self):
        user = UserFactory(is_active=False)
        assert SigninGuardModelBackend().get_user(user.pk) is None

    def test_allauth_backend_drops_inactive_user(self):
        user = UserFactory(is_active=False)
        assert SigninGuardAllauthBackend().get_user(user.pk) is None

    def test_backends_drop_deactivated_user(self):
        user = UserFactory()
        user.is_active = False
        user.deactivated_at = timezone.now()
        user.save(update_fields=["is_active", "deactivated_at"])

        assert SigninGuardModelBackend().get_user(user.pk) is None
        assert SigninGuardAllauthBackend().get_user(user.pk) is None

    def test_authenticate_still_rejects_inactive_user(self):
        user = UserFactory(is_active=False)
        user.set_password(_LOGIN_VALUE)
        user.save(update_fields=["password"])

        assert authenticate(username=user.username, password=_LOGIN_VALUE) is None


class TestDeactivatedSessionInvalidation:
    def test_deactivating_ends_existing_session(self, client):
        user = UserFactory()
        user.set_password(_LOGIN_VALUE)
        user.save(update_fields=["password"])
        client.force_login(user)
        assert client.get(SETTINGS_URL).status_code == HTTP_OK

        user.is_active = False
        user.deactivated_at = timezone.now()
        user.save(update_fields=["is_active", "deactivated_at"])

        assert client.get(SETTINGS_URL).status_code == HTTP_FORBIDDEN
