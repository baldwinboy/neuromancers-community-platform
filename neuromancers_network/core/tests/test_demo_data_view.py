from __future__ import annotations

from http import HTTPStatus

import pytest
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _admin_non_superuser():
    user = UserFactory(is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtailadmin",
            codename="access_admin",
        ),
    )
    return user


def test_demo_data_view_requires_superuser(client):
    client.force_login(_admin_non_superuser())

    response = client.get(reverse("demo_data"))

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_demo_data_view_loads_for_superuser(client):
    client.force_login(UserFactory(is_superuser=True))

    response = client.get(reverse("demo_data"))

    assert response.status_code == HTTPStatus.OK
    assert "Seed demo data" in response.content.decode()


@override_settings(DEMO_DATA_ENABLED=False)
def test_demo_data_view_respects_feature_flag(client):
    client.force_login(UserFactory(is_superuser=True))

    response = client.get(reverse("demo_data"))

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_demo_data_seed_form_requires_password(client):
    client.force_login(UserFactory(is_superuser=True))

    response = client.post(
        reverse("demo_data"),
        {
            "action": "seed",
            "email_base": "example@mail.com",
            "password": "",
            "confirm": "on",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "This field is required" in response.content.decode()
