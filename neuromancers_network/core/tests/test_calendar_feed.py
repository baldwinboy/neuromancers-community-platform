import pytest
from django.test import Client

from neuromancers_network.core.models import CalendarFeedToken
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

HTTP_OK = 200
HTTP_NOT_FOUND = 404
ABSENT_FEED_UUID = "00000000-0000-0000-0000-000000000000"


class TestCalendarFeedView:
    def test_unknown_token_returns_404(self):
        response = Client().get(f"/calendar/{ABSENT_FEED_UUID}.ics")

        assert response.status_code == HTTP_NOT_FOUND

    def test_valid_token_returns_calendar(self):
        token = CalendarFeedToken.objects.create(user=UserFactory())

        response = Client().get(f"/calendar/{token.token}.ics")

        assert response.status_code == HTTP_OK
        assert response["Content-Type"].startswith("text/calendar")
        assert response.content.startswith(b"BEGIN:VCALENDAR")

    def test_inactive_token_returns_404(self):
        token = CalendarFeedToken.objects.create(user=UserFactory(), is_active=False)

        response = Client().get(f"/calendar/{token.token}.ics")

        assert response.status_code == HTTP_NOT_FOUND
