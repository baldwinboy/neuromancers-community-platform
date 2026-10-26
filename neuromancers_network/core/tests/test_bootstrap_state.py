from __future__ import annotations

import json

from neuromancers_network.core.bootstrap_state import BootstrapPhase
from neuromancers_network.core.bootstrap_state import read_status
from neuromancers_network.core.bootstrap_state import write_status

REVISION = "a" * 40
OTHER_REVISION = "b" * 40


def test_missing_state_is_pending(tmp_path):
    status = read_status(tmp_path, REVISION)

    assert status.phase is BootstrapPhase.PENDING
    assert not status.serving_allowed


def test_write_and_read_round_trip(tmp_path):
    write_status(tmp_path, REVISION, BootstrapPhase.COMPLETE)

    status = read_status(tmp_path, REVISION)

    assert status.phase is BootstrapPhase.COMPLETE
    assert status.serving_allowed


def test_other_revision_is_pending(tmp_path):
    write_status(tmp_path, OTHER_REVISION, BootstrapPhase.COMPLETE)

    status = read_status(tmp_path, REVISION)

    assert status.phase is BootstrapPhase.PENDING


def test_invalid_json_is_pending(tmp_path, caplog):
    (tmp_path / "state.json").write_text("{invalid", encoding="utf-8")

    status = read_status(tmp_path, REVISION)

    assert status.phase is BootstrapPhase.PENDING
    assert "Could not read bootstrap state" in caplog.text


def test_unknown_phase_is_pending(tmp_path, caplog):
    (tmp_path / "state.json").write_text(
        json.dumps({"revision": REVISION, "phase": "unknown"}),
        encoding="utf-8",
    )

    status = read_status(tmp_path, REVISION)

    assert status.phase is BootstrapPhase.PENDING
    assert "Invalid bootstrap phase" in caplog.text


def test_writer_leaves_no_temporary_files(tmp_path):
    write_status(tmp_path, REVISION, BootstrapPhase.MIGRATING)

    assert sorted(path.name for path in tmp_path.iterdir()) == ["state.json"]
