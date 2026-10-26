from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.management import call_command

from neuromancers_network.core.bootstrap_state import BootstrapPhase
from neuromancers_network.core.bootstrap_state import BootstrapStatus
from neuromancers_network.core.bootstrap_state import read_status

REVISION = "a" * 40
BOOTSTRAP_COMMAND = (
    "neuromancers_network.core.management.commands.bootstrap.call_command"
)
WAIT_COMMAND = (
    "neuromancers_network.core.management.commands.wait_for_bootstrap.current_status"
)


def _configure(settings, tmp_path):
    settings.BOOTSTRAP_STATE_DIR = str(tmp_path)
    settings.GIT_COMMIT_SHA = REVISION
    settings.BOOTSTRAP_GATE_ENABLED = True


def test_bootstrap_writes_phases_and_commands(settings, tmp_path):
    _configure(settings, tmp_path)

    with patch(BOOTSTRAP_COMMAND) as call:
        call_command("bootstrap")

    assert read_status(tmp_path, REVISION).phase is BootstrapPhase.COMPLETE
    assert [item.args[0] for item in call.call_args_list] == [
        "migrate",
        "ensure_superuser",
        "seed_help_guide",
        "seed_pages",
        "seed_account_selfservice",
    ]


def test_bootstrap_marks_migrate_failure(settings, tmp_path):
    _configure(settings, tmp_path)

    with (
        patch(BOOTSTRAP_COMMAND, side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        call_command("bootstrap")

    assert read_status(tmp_path, REVISION).phase is BootstrapPhase.FAILED_MIGRATE


def test_bootstrap_marks_seed_failure(settings, tmp_path):
    _configure(settings, tmp_path)

    with (
        patch(BOOTSTRAP_COMMAND, side_effect=[None, RuntimeError("boom")]),
        pytest.raises(RuntimeError, match="boom"),
    ):
        call_command("bootstrap")

    assert read_status(tmp_path, REVISION).phase is BootstrapPhase.FAILED_BOOTSTRAP


def test_wait_for_bootstrap_returns_when_complete(settings, tmp_path):
    _configure(settings, tmp_path)

    statuses = [
        BootstrapStatus(revision=REVISION, phase=BootstrapPhase.COMPLETE),
    ]
    with patch(WAIT_COMMAND, side_effect=statuses):
        call_command("wait_for_bootstrap")


def test_wait_for_bootstrap_does_not_exit_on_failure(settings, tmp_path):
    _configure(settings, tmp_path)

    statuses = [
        BootstrapStatus(revision=REVISION, phase=BootstrapPhase.FAILED_MIGRATE),
        BootstrapStatus(revision=REVISION, phase=BootstrapPhase.COMPLETE),
    ]
    with (
        patch(WAIT_COMMAND, side_effect=statuses),
        patch(
            "neuromancers_network.core.management.commands.wait_for_bootstrap.time.sleep",
        ) as sleep,
    ):
        call_command("wait_for_bootstrap")

    sleep.assert_called_once()


def test_wait_for_bootstrap_is_noop_when_gate_disabled(settings):
    settings.BOOTSTRAP_GATE_ENABLED = False

    with patch(WAIT_COMMAND) as current:
        call_command("wait_for_bootstrap")

    current.assert_not_called()
