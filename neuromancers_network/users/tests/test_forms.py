import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from neuromancers_network.users.forms import UserSignupForm

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


class TestUserSignupForm:
    def test_accept_tos_is_required(self):
        form = UserSignupForm(data=signup_data(accept_tos=False))

        assert not form.is_valid()
        assert "accept_tos" in form.errors

    def test_save_persists_accepted_tos(self):
        client = Client()
        response = client.post(reverse("account_signup"), data=signup_data())

        assert response.status_code in (302, 200)

        user = get_user_model().objects.get(username="newcomer")
        user.refresh_from_db()
        assert user.accepted_tos is True
