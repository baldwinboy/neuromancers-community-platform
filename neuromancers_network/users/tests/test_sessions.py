import logging

import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session

from neuromancers_network.users.sessions import active_session_keys
from neuromancers_network.users.sessions import revoke_sessions
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _make_session(user) -> str:
    store = SessionStore()
    store[SESSION_KEY] = str(user.pk)
    store.create()
    return store.session_key


class TestRevokeSessions:
    def test_lists_only_owned_sessions(self):
        user = UserFactory()
        mine = _make_session(user)
        _make_session(UserFactory())

        assert active_session_keys(user) == [mine]

    def test_revoke_all(self):
        user = UserFactory()
        first = _make_session(user)
        second = _make_session(user)
        other = _make_session(UserFactory())

        revoke_sessions(user)

        assert not Session.objects.filter(session_key__in=[first, second]).exists()
        assert Session.objects.filter(session_key=other).exists()

    def test_keep_current(self):
        user = UserFactory()
        current = _make_session(user)
        other = _make_session(user)

        revoke_sessions(user, keep_current=current)

        assert Session.objects.filter(session_key=current).exists()
        assert not Session.objects.filter(session_key=other).exists()

    def test_caps_active_session_keys(self, monkeypatch, caplog):
        user = UserFactory()
        cap = 2
        for _index in range(3):
            _make_session(user)
        monkeypatch.setattr(
            "neuromancers_network.users.sessions.MAX_ACTIVE_SESSION_KEYS",
            cap,
        )

        with caplog.at_level(
            logging.WARNING,
            logger="neuromancers_network.users.sessions",
        ):
            keys = active_session_keys(user)

        assert len(keys) == cap
        assert "Capped active session keys" in caplog.text
