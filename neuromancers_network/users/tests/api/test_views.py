"""User API identity updates."""

from __future__ import annotations

import json
from http import HTTPStatus

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from neuromancers_network.core.models import ModerationSettings
from neuromancers_network.users.tests.factories import UserFactory
from neuromancers_network.users.validators import CACHE_KEY

pytestmark = pytest.mark.django_db

USERNAME = "new_name"


def patch_me(client, *, username=USERNAME, name="New Name"):
    return client.patch(
        "/api/users/me/",
        data=json.dumps({"username": username, "name": name}),
        content_type="application/json",
    )


class TestUpdateCurrentUser:
    def test_updates_and_normalises_username(self):
        user = UserFactory(username="old_name")
        client = Client()
        client.force_login(user)

        response = patch_me(client)

        assert response.status_code == HTTPStatus.OK
        user.refresh_from_db()
        assert user.username == USERNAME
        assert user.name == "New Name"
        assert user.username_changed_at is not None

    def test_rejects_duplicate_username(self):
        UserFactory(username=USERNAME)
        user = UserFactory(username="old_name")
        client = Client()
        client.force_login(user)

        response = patch_me(client)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        user.refresh_from_db()
        assert user.username == "old_name"

    def test_rejects_change_during_cooldown(self):
        user = UserFactory(username="old_name")
        user.username_changed_at = timezone.now()
        user.save(update_fields=["username_changed_at"])
        client = Client()
        client.force_login(user)

        response = patch_me(client)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        user.refresh_from_db()
        assert user.username == "old_name"

    def test_rejects_blocked_username(self):
        settings_obj = ModerationSettings.load()
        settings_obj.username_blocklist = USERNAME
        settings_obj.save()
        cache.delete(CACHE_KEY)
        user = UserFactory(username="old_name")
        client = Client()
        client.force_login(user)

        response = patch_me(client)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        user.refresh_from_db()
        assert user.username == "old_name"
