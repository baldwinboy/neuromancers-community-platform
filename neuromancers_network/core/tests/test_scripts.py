from __future__ import annotations

import pytest
from django.core import signing

from neuromancers_network.core.consent import COOKIE_NAME
from neuromancers_network.core.consent import SIGNING_SALT
from neuromancers_network.core.models import HomePage
from neuromancers_network.core.models import ScriptsSetting
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _script(name, category, placement, code, *, audience=None):
    return (
        "script",
        {
            "name": name,
            "category": category,
            "placement": placement,
            "audience": audience or [],
            "code": code,
        },
    )


def _configure():
    config = ScriptsSetting.load()
    config.scripts = [
        _script("Necessary", "necessary", "head", '<script id="necessary"></script>'),
        _script("Analytics", "analytics", "head", '<script id="analytics"></script>'),
        _script("Marketing", "marketing", "body", '<script id="marketing"></script>'),
        _script(
            "Member",
            "necessary",
            "body",
            '<script id="member"></script>',
            audience=["authenticated"],
        ),
    ]
    config.save()
    return config


def _home():
    home = HomePage.objects.first()
    assert home is not None
    return home


def _render(client):
    return client.get(_home().get_url()).content.decode()


def _consent(client, categories):
    client.cookies[COOKIE_NAME] = signing.dumps(
        {"categories": categories, "version": 1},
        salt=SIGNING_SALT,
    )


class TestScriptInjection:
    def test_necessary_only_without_consent(self, client):
        _configure()

        html = _render(client)

        assert 'id="necessary"' in html
        assert 'id="analytics"' not in html
        assert 'id="marketing"' not in html
        assert 'id="member"' not in html

    def test_consented_categories_render(self, client):
        _configure()
        _consent(client, ["analytics"])

        html = _render(client)

        assert 'id="analytics"' in html
        assert 'id="marketing"' not in html

    def test_marketing_requires_its_own_consent(self, client):
        _configure()
        _consent(client, ["analytics", "marketing"])

        html = _render(client)

        assert 'id="analytics"' in html
        assert 'id="marketing"' in html

    def test_audience_gates_member_scripts(self, client):
        _configure()
        client.force_login(UserFactory())

        html = _render(client)

        assert 'id="member"' in html

    def test_invalid_consent_cookie_is_ignored(self, client):
        _configure()
        client.cookies[COOKIE_NAME] = "not-a-signed-value"

        html = _render(client)

        assert 'id="necessary"' in html
        assert 'id="analytics"' not in html

    def test_no_scripts_configured_renders_nothing(self, client):
        html = _render(client)

        assert "<script id=" not in html
