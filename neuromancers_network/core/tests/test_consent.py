from __future__ import annotations

import pytest
from django.core import signing
from django.test import Client
from django.urls import reverse

from neuromancers_network.core.consent import COOKIE_NAME
from neuromancers_network.core.consent import SIGNING_SALT
from neuromancers_network.core.consent import read_consent
from neuromancers_network.core.models import ConsentSettings
from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import ScriptsSetting

pytestmark = pytest.mark.django_db

OK = 200
FOUND = 302
BAD_REQUEST = 400
FORBIDDEN = 403


def _home():
    home = HomePage.objects.first()
    assert home is not None
    return home


def _configure_scripts():
    config = ScriptsSetting.load()
    config.scripts = [
        (
            "script",
            {
                "name": "Analytics",
                "category": "analytics",
                "placement": "body",
                "audience": [],
                "code": '<script id="analytics"></script>',
            },
        ),
    ]
    config.save()


def _settings(version="1"):
    config = ConsentSettings.load()
    config.policy_version = version
    config.save()
    return config


def _accept(client, *, categories=(), version="1", choice="accept"):
    return client.post(
        reverse("consent_accept"),
        {
            "policy_version": version,
            "return_to": "/",
            "choice": choice,
            "categories": list(categories),
        },
    )


class TestBanner:
    def test_visible_without_consent(self, client):
        _settings()

        response = client.get(_home().get_url())

        assert response.status_code == OK
        assert 'id="consent-title"' in response.content.decode()

    def test_hidden_after_accepting(self, client):
        _settings()
        _accept(client)

        html = client.get(_home().get_url()).content.decode()

        assert 'id="consent-title"' not in html

    def test_reset_reopens_the_banner(self, client):
        _settings()
        _accept(client)
        client.post(reverse("consent_reset"), {"return_to": "/"})

        html = client.get(_home().get_url()).content.decode()

        assert 'id="consent-title"' in html


class TestConsentChoices:
    def test_necessary_only_suppresses_optional_scripts(self, client):
        _settings()
        _configure_scripts()

        _accept(client, choice="necessary")
        html = client.get(_home().get_url()).content.decode()

        assert 'id="analytics"' not in html

    def test_accepting_analytics_enables_its_scripts(self, client):
        _settings()
        _configure_scripts()

        response = _accept(client, categories=["analytics"])
        html = client.get(_home().get_url()).content.decode()

        assert response.status_code == FOUND
        assert 'id="analytics"' in html
        cookie = client.cookies[COOKIE_NAME].value
        payload = signing.loads(cookie, salt=SIGNING_SALT)
        assert payload["categories"] == ["analytics"]

    def test_unknown_category_is_rejected(self, client):
        _settings()

        response = _accept(client, categories=["necessary"])

        assert response.status_code == BAD_REQUEST

    def test_stale_version_is_rejected(self, client):
        _settings(version="2")

        response = _accept(client, version="1")

        assert response.status_code == BAD_REQUEST

    def test_version_bump_reasks(self, client):
        config = _settings()
        _accept(client)
        assert (
            'id="consent-title"'
            not in client.get(
                _home().get_url(),
            ).content.decode()
        )

        config.policy_version = "2"
        config.save()

        html = client.get(_home().get_url()).content.decode()
        assert 'id="consent-title"' in html


class TestConsentTransport:
    def test_read_consent_round_trip(self, client):
        _settings()
        _accept(client, categories=["analytics"])

        request = type(
            "Request",
            (),
            {
                "COOKIES": {
                    COOKIE_NAME: client.cookies[COOKIE_NAME].value,
                },
            },
        )()

        assert read_consent(request)["categories"] == ["analytics"]

    def test_vary_cookie_is_set(self, client):
        _settings()

        response = client.get(_home().get_url())

        assert "Cookie" in response["Vary"]

    def test_csrf_is_enforced(self):
        _settings()
        client = Client(enforce_csrf_checks=True)

        response = _accept(client)

        assert response.status_code == FORBIDDEN
