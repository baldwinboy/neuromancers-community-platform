from __future__ import annotations

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import override_settings

from neuromancers_network.core.demo_data import DemoDataError
from neuromancers_network.core.demo_data import cleanup_demo_data
from neuromancers_network.core.demo_data import demo_data_status
from neuromancers_network.core.demo_data import parse_demo_email_base
from neuromancers_network.core.demo_data import seed_demo_data
from neuromancers_network.core.demo_data import validate_test_stripe_keys
from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import StandardPage
from neuromancers_network.core.models import StripeSettings
from neuromancers_network.core.models.pages import MeetingIndexPage
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

User = get_user_model()


def _configure_test_stripe():
    config = StripeSettings.load()
    config.publishable_key = "pk_test_demo"
    config.secret_key = "sk_test_demo"  # noqa: S105
    config.save()


def _home():
    home = HomePage.objects.first()
    assert home is not None
    return home


def test_parse_demo_email_base():
    assert parse_demo_email_base("Example@Mail.com") == ("example", "mail.com")
    assert parse_demo_email_base("example+tag@mail.com") == ("example", "mail.com")


def test_validate_test_stripe_keys_rejects_live_keys():
    _configure_test_stripe()
    config = StripeSettings.load()
    config.secret_key = "sk_live_nope"  # noqa: S105
    config.save()

    with pytest.raises(DemoDataError, match="live"):
        validate_test_stripe_keys()


def test_seed_and_cleanup_demo_data():
    user_count = 4
    peer_count = 2
    meeting_count = 3
    review_count = 1

    _configure_test_stripe()
    real_user = UserFactory(username="real-user", email="real@example.com")

    result = seed_demo_data(
        email_base="example@mail.com",
        password="demo-pass-123",  # noqa: S106
        include_paused_peer=True,
    )

    assert result["users"] == user_count
    assert result["peers"] == peer_count
    assert result["seekers"] == peer_count
    assert result["meetings"] == meeting_count
    assert result["bookings"] == meeting_count
    assert result["reviews"] == review_count
    assert result["refunds"] == review_count

    peer = User.objects.get(username="demo-peer-01")
    assert peer.email == "example+demo-peer-01@mail.com"
    assert peer.check_password("demo-pass-123")
    address = EmailAddress.objects.get(user=peer)
    assert address.verified is True
    assert address.primary is True

    status = demo_data_status(email_base="example@mail.com")
    assert status["users"] == user_count
    assert "example@mail.com" in status["email_bases"]

    cleanup_demo_data(email_base="example@mail.com")

    assert not User.objects.filter(username__startswith="demo-").exists()
    assert User.objects.filter(pk=real_user.pk).exists()
    assert demo_data_status()["users"] == 0


def test_seed_refuses_a_different_base_while_demo_users_exist():
    _configure_test_stripe()
    _home()
    seed_demo_data(
        email_base="example@mail.com",
        password="demo-pass-123",  # noqa: S106
    )

    with pytest.raises(DemoDataError, match="different base"):
        seed_demo_data(
            email_base="other@mail.com",
            password="demo-pass-123",  # noqa: S106
        )


def test_seed_tolerates_an_existing_meetings_page():
    user_count = 4

    _configure_test_stripe()
    home = _home()
    home.add_child(instance=StandardPage(title="Meetings", slug="meetings"))

    result = seed_demo_data(
        email_base="example@mail.com",
        password="demo-pass-123",  # noqa: S106
    )

    assert result["users"] == user_count
    assert StandardPage.objects.filter(slug="meetings").exists()
    assert MeetingIndexPage.objects.child_of(home).exists()


@override_settings(DEMO_DATA_ENABLED=False)
def test_disabled_flag_blocks_seed():
    _configure_test_stripe()

    with pytest.raises(DemoDataError, match="disabled"):
        seed_demo_data(
            email_base="example@mail.com",
            password="demo-pass-123",  # noqa: S106
        )
