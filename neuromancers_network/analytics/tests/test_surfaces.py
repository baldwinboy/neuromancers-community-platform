from __future__ import annotations

import pytest
from django.urls import reverse

from neuromancers_network.analytics.metrics import RevenueSummary
from neuromancers_network.analytics.panels import AnalyticsPanel
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PLATFORM_URL = "/api/analytics/platform"
ME_URL = "/api/analytics/me"
SUCCESS = 200
BAD_REQUEST = 400
UNAUTHORIZED = 401
FORBIDDEN = 403


class TestDashboard:
    def test_staff_can_open(self, client):
        client.force_login(UserFactory(is_superuser=True))

        response = client.get(reverse("analytics_dashboard"))

        assert response.status_code == SUCCESS
        assert "Analytics" in response.content.decode()

    def test_member_cannot_open(self, client):
        client.force_login(UserFactory())

        response = client.get(reverse("analytics_dashboard"))

        assert response.status_code in (302, 403)

    def test_panel_shows_combined_revenue(self):
        context = AnalyticsPanel().get_context_data({})
        revenue = context["revenue"]

        assert context["analytics_url"]
        assert revenue.combined == revenue.marketplace + revenue.subscription

    def test_revenue_summary_caches_the_combined_total(self):
        combined_count = 15
        summary = RevenueSummary(marketplace=10, subscription=5)

        assert summary.combined == combined_count
        assert summary.combined == summary.combined


class TestAnalyticsAPI:
    def test_platform_requires_staff(self, client):
        client.force_login(UserFactory())

        assert client.get(PLATFORM_URL).status_code == FORBIDDEN

    def test_anonymous_is_unauthorized(self, client):
        assert client.get(PLATFORM_URL).status_code == UNAUTHORIZED

    def test_staff_reads_platform_metrics(self, client):
        client.force_login(UserFactory(is_staff=True))

        response = client.get(f"{PLATFORM_URL}?period=this_month")

        assert response.status_code == SUCCESS
        body = response.json()
        assert "gbv" in body
        assert "subscription_revenue" in body

    def test_member_reads_self_scope(self, client):
        client.force_login(UserFactory())

        response = client.get(ME_URL)

        assert response.status_code == SUCCESS
        assert "spend" in response.json()

    def test_invalid_period_is_400(self, client):
        client.force_login(UserFactory(is_staff=True))

        response = client.get(f"{PLATFORM_URL}?period=fortnight")

        assert response.status_code == BAD_REQUEST
