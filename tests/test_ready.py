from __future__ import annotations

import pytest
from django.test import Client
from django.test import override_settings

from neuromancers_network.core.bootstrap_state import BootstrapPhase
from neuromancers_network.core.bootstrap_state import write_status

pytestmark = pytest.mark.django_db

SHA = "a" * 40
OK = 200
UNAVAILABLE = 503


def test_ready_is_ready_when_gate_disabled():
    with override_settings(BOOTSTRAP_GATE_ENABLED=False, GIT_COMMIT_SHA=SHA):
        response = Client().get("/api/ready")

    assert response.status_code == OK
    assert response.json() == {"status": "ready", "revision": SHA}


def test_ready_reports_complete(tmp_path):
    write_status(tmp_path, SHA, BootstrapPhase.COMPLETE)

    with override_settings(
        BOOTSTRAP_GATE_ENABLED=True,
        BOOTSTRAP_STATE_DIR=str(tmp_path),
        GIT_COMMIT_SHA=SHA,
    ):
        response = Client().get("/api/ready")

    assert response.status_code == OK
    assert response.json() == {"status": "ready", "revision": SHA}


def test_ready_reports_seeding(tmp_path):
    write_status(tmp_path, SHA, BootstrapPhase.SEEDING)

    with override_settings(
        BOOTSTRAP_GATE_ENABLED=True,
        BOOTSTRAP_STATE_DIR=str(tmp_path),
        GIT_COMMIT_SHA=SHA,
    ):
        response = Client().get("/api/ready")

    assert response.status_code == UNAVAILABLE
    assert response.json() == {"status": "seeding", "revision": SHA}


def test_ready_reports_failed_migrate(tmp_path):
    write_status(tmp_path, SHA, BootstrapPhase.FAILED_MIGRATE)

    with override_settings(
        BOOTSTRAP_GATE_ENABLED=True,
        BOOTSTRAP_STATE_DIR=str(tmp_path),
        GIT_COMMIT_SHA=SHA,
    ):
        response = Client().get("/api/ready")

    assert response.status_code == UNAVAILABLE
    assert response.json() == {"status": "failed-migrate", "revision": SHA}


def test_health_is_liveness_only_on_failure(tmp_path):
    write_status(tmp_path, SHA, BootstrapPhase.FAILED_MIGRATE)

    with override_settings(
        BOOTSTRAP_GATE_ENABLED=True,
        BOOTSTRAP_STATE_DIR=str(tmp_path),
        GIT_COMMIT_SHA=SHA,
    ):
        response = Client().get("/api/health")

    assert response.status_code == OK
    assert response.json() == {"status": "ok", "revision": SHA}


def test_gate_blocks_normal_routes_while_pending(tmp_path):
    with override_settings(
        BOOTSTRAP_GATE_ENABLED=True,
        BOOTSTRAP_STATE_DIR=str(tmp_path),
        GIT_COMMIT_SHA=SHA,
    ):
        response = Client().get("/")

    assert response.status_code == UNAVAILABLE
