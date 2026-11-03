from __future__ import annotations

import pytest

from neuromancers_network.core.email_seed import seed_email_templates
from neuromancers_network.core.management.commands.seed_dashboard import seed_dashboard
from neuromancers_network.core.management.commands.seed_pages import seed_pages
from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models.pages import DashboardPage
from neuromancers_network.core.models.pages import MeetingIndexPage
from neuromancers_network.core.models.pages import PeerIndexPage
from neuromancers_network.core.models.pages import SettingsPage
from neuromancers_network.core.models.pages import StandardPage

pytestmark = pytest.mark.django_db


def test_seed_pages_creates_the_phase_b_tree():
    seed_pages()

    home = HomePage.objects.live().first()
    assert home is not None
    sessions = MeetingIndexPage.objects.get()
    providers = PeerIndexPage.objects.get()
    assert sessions.slug == "sessions"
    assert sessions.title == "Sessions"
    assert providers.slug == "care-providers"
    assert providers.title == "Care Providers"

    for slug in (
        "my-bookings",
        "my-reviews",
        "my-bookmarks",
        "provider-bookings",
        "manage-sessions",
        "provider-reviews",
        "join-the-network",
        "dashboard",
    ):
        assert home.get_children().filter(slug=slug).exists(), slug

    assert not SettingsPage.objects.exists()
    assert StandardPage.objects.filter(slug="diary").exists() is False


def test_dashboard_seed_replaces_settings():
    seed_pages()
    seed_dashboard(force=True)

    page = DashboardPage.objects.get()
    assert page.body
    assert "Plan + Billing" in str(page.body)
    assert "Manage subscription" in str(page.body)
    assert "Pause plan" not in str(page.body)
    assert "Resume plan" not in str(page.body)
    assert "Cancel plan" not in str(page.body)


def test_email_seed_is_idempotent():
    from wagtail_daisIE.allauth_emails.models import AllauthEmailOverride  # noqa: PLC0415
    from wagtail_daisIE.notifications.models import EmailTemplate  # noqa: PLC0415

    from neuromancers_network.inbox.models import DaisieBridgeSubscriber  # noqa: PLC0415

    seed_email_templates()
    seed_email_templates()

    assert EmailTemplate.objects.filter(template_key="account_created").exists()
    assert EmailTemplate.objects.filter(template_key="peer_approved").exists()
    assert AllauthEmailOverride.objects.filter(is_active=True).exists()
    assert DaisieBridgeSubscriber.objects.filter(is_active=True).exists()
