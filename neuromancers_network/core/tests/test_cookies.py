from __future__ import annotations

import pytest

from neuromancers_network.core.models import Cookie
from neuromancers_network.core.models import CookieCategory
from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import StandardPage
from neuromancers_network.core.page_blocks import CookieRegistryBlock

pytestmark = pytest.mark.django_db

OK = 200
SEEDED_NAMES = {"django_language", "daisie_theme", "sessionid", "csrftoken"}


def _home():
    home = HomePage.objects.first()
    assert home is not None
    return home


class TestCookieRegistry:
    def test_required_cookies_are_seeded_as_necessary(self):
        rows = Cookie.objects.filter(name__in=SEEDED_NAMES)

        assert {row.name for row in rows} == SEEDED_NAMES
        assert all(row.category == CookieCategory.NECESSARY for row in rows)

    def test_categories_are_shared_with_the_banner(self):
        assert list(CookieCategory.values) == ["necessary", "analytics", "marketing"]

    def test_block_groups_active_cookies_by_category(self):
        Cookie.objects.create(
            name="_ga",
            category=CookieCategory.ANALYTICS,
            provider="Google",
        )
        Cookie.objects.create(
            name="retired",
            category=CookieCategory.MARKETING,
            is_active=False,
        )

        context = CookieRegistryBlock().get_context(None, {})

        groups = context["cookie_groups"]
        labels = {group["value"]: group["label"] for group in groups}
        assert labels["analytics"] == "Analytics"
        names = {cookie.name for group in groups for cookie in group["cookies"]}
        assert "_ga" in names
        assert "retired" not in names
        assert names >= SEEDED_NAMES


class TestPolicyPage:
    def test_policy_page_renders_the_registry(self, client):
        home = _home()
        page = StandardPage(title="Cookie policy", slug="cookie-policy")
        page.body = [("cookie_registry", None)]
        home.add_child(instance=page)
        page.save_revision().publish()

        response = client.get(page.get_url())

        assert response.status_code == OK
        html = response.content.decode()
        for name in SEEDED_NAMES:
            assert name in html
        assert "Necessary" in html
