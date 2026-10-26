from __future__ import annotations

from unittest.mock import Mock

from django.http import HttpResponse
from django.test import RequestFactory

from neuromancers_network.core.bootstrap_state import BootstrapPhase
from neuromancers_network.core.bootstrap_state import write_status
from neuromancers_network.core.middleware import BootstrapGateMiddleware

REVISION = "a" * 40
OK = 200
UNAVAILABLE = 503


def _configure(settings, tmp_path, *, enabled=True):
    settings.BOOTSTRAP_STATE_DIR = str(tmp_path)
    settings.GIT_COMMIT_SHA = REVISION
    settings.BOOTSTRAP_GATE_ENABLED = enabled


def _middleware():
    get_response = Mock(return_value=HttpResponse("ok"))
    return BootstrapGateMiddleware(get_response), get_response


def test_gate_disabled_passes_through(settings, tmp_path):
    _configure(settings, tmp_path, enabled=False)
    middleware, get_response = _middleware()

    response = middleware(RequestFactory().get("/"))

    assert response.status_code == OK
    get_response.assert_called_once()


def test_gate_blocks_pending_state(settings, tmp_path):
    _configure(settings, tmp_path)
    middleware, get_response = _middleware()

    response = middleware(RequestFactory().get("/"))

    assert response.status_code == UNAVAILABLE
    assert response["Retry-After"] == "30"
    assert response["Cache-Control"] == "no-store"
    get_response.assert_not_called()


def test_gate_allows_complete_state(settings, tmp_path):
    _configure(settings, tmp_path)
    write_status(tmp_path, REVISION, BootstrapPhase.COMPLETE)
    middleware, get_response = _middleware()

    response = middleware(RequestFactory().get("/"))

    assert response.status_code == OK
    get_response.assert_called_once()


def test_gate_exempts_health_readiness_and_static(settings, tmp_path):
    _configure(settings, tmp_path)
    middleware, get_response = _middleware()
    exempt_paths = ("/api/health", "/api/ready", "/static/app.css", "/media/file.png")

    for path in exempt_paths:
        response = middleware(RequestFactory().get(path))
        assert response.status_code == OK, path

    assert get_response.call_count == len(exempt_paths)


def test_gate_blocks_corrupt_state(settings, tmp_path):
    _configure(settings, tmp_path)
    (tmp_path / "state.json").write_text("{invalid", encoding="utf-8")
    middleware, get_response = _middleware()

    response = middleware(RequestFactory().get("/"))

    assert response.status_code == UNAVAILABLE
    get_response.assert_not_called()
