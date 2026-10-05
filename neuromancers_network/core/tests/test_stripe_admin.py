import pytest
from django.test import Client

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

HTTP_OK = 200
HTTP_FORBIDDEN = 403
PUBLISHABLE_KEY = "pk_test_123"
SECRET_KEY = "sk_test_123"  # noqa: S105


def make_admin():
    user = UserFactory()
    user.activate_staff()
    user.is_superuser = True
    user.save()
    return user


def configure_stripe():
    config = StripeSettings.load()
    config.publishable_key = PUBLISHABLE_KEY
    config.secret_key = SECRET_KEY
    config.save()
    return config


class TestStripeSyncView:
    def test_forbidden_when_not_ready(self):
        client = Client()
        client.force_login(make_admin())

        response = client.get("/cms/stripe/sync/")

        assert response.status_code == HTTP_FORBIDDEN

    def test_ok_when_ready(self):
        configure_stripe()
        client = Client()
        client.force_login(make_admin())

        response = client.get("/cms/stripe/sync/")

        assert response.status_code == HTTP_OK


class TestStripeWebhookView:
    def test_forbidden_when_not_ready(self):
        client = Client()
        client.force_login(make_admin())

        response = client.get("/cms/stripe/webhook/")

        assert response.status_code == HTTP_FORBIDDEN

    def test_ok_when_ready(self):
        configure_stripe()
        client = Client()
        client.force_login(make_admin())

        response = client.get("/cms/stripe/webhook/")

        assert response.status_code == HTTP_OK
