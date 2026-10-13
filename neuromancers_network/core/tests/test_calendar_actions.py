import pytest
from django.test import RequestFactory

from neuromancers_network.core.actions import calendar_revoke_token
from neuromancers_network.core.actions import calendar_rotate_token
from neuromancers_network.core.models import CalendarFeedToken
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _request(user):
    request = RequestFactory().post("/")
    request.user = user
    return request


class TestCalendarTokenActions:
    def test_revoke_deactivates(self):
        user = UserFactory()
        token = CalendarFeedToken.objects.create(user=user)

        calendar_revoke_token(_request(user), {})

        token.refresh_from_db()
        assert token.is_active is False

    def test_rotate_replaces_token(self):
        user = UserFactory()
        token = CalendarFeedToken.objects.create(user=user)
        previous = token.token

        calendar_rotate_token(_request(user), {})

        token.refresh_from_db()
        assert token.token != previous
        assert token.is_active is True
