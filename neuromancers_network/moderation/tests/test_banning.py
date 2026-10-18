from datetime import timedelta

import pytest
from django.utils import timezone

from neuromancers_network.moderation.banning import email_is_banned
from neuromancers_network.moderation.banning import ip_is_banned
from neuromancers_network.moderation.models import EmailBan
from neuromancers_network.moderation.models import IPBan

pytestmark = pytest.mark.django_db


class TestEmailBan:
    def test_matches_legacy_mixed_case_values(self):
        exact = EmailBan.objects.create(value="bad@example.com")
        EmailBan.objects.filter(pk=exact.pk).update(value="Bad@Example.com")
        domain = EmailBan.objects.create(value="blocked.test", is_domain=True)
        EmailBan.objects.filter(pk=domain.pk).update(value="Blocked.Test")

        assert email_is_banned("bad@example.com") is True
        assert email_is_banned("anyone@blocked.test") is True

    def test_values_are_normalised_on_save(self):
        ban = EmailBan.objects.create(value="  Mixed@Example.COM  ")

        assert ban.value == "mixed@example.com"
        assert EmailBan.objects.get(pk=ban.pk).value == "mixed@example.com"

    def test_exact_domain_and_inactive(self):
        EmailBan.objects.create(value="bad@example.com")
        EmailBan.objects.create(value="blocked.test", is_domain=True)
        EmailBan.objects.create(value="off@example.com", is_active=False)

        assert email_is_banned("bad@example.com") is True
        assert email_is_banned("BAD@example.com") is True
        assert email_is_banned("anyone@blocked.test") is True
        assert email_is_banned("off@example.com") is False
        assert email_is_banned("good@example.com") is False


class TestIPBan:
    def test_expiry(self):
        IPBan.objects.create(
            ip_address="203.0.113.9",
            expires_at=timezone.now() + timedelta(days=1),
        )
        IPBan.objects.create(
            ip_address="203.0.113.10",
            expires_at=timezone.now() - timedelta(days=1),
        )

        assert ip_is_banned("203.0.113.9") is True
        assert ip_is_banned("203.0.113.10") is False
        assert ip_is_banned("203.0.113.11") is False
