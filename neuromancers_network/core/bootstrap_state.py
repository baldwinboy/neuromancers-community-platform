"""Deployment bootstrap state shared by web, init, and Celery containers."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

STATE_FILE_NAME = "state.json"


class BootstrapPhase(StrEnum):
    PENDING = "pending"
    MIGRATING = "migrating"
    SEEDING = "seeding"
    COMPLETE = "complete"
    FAILED_MIGRATE = "failed-migrate"
    FAILED_BOOTSTRAP = "failed-bootstrap"


@dataclass(frozen=True)
class BootstrapStatus:
    revision: str
    phase: BootstrapPhase

    @property
    def serving_allowed(self) -> bool:
        return self.phase is BootstrapPhase.COMPLETE


def _state_path(state_dir: str | Path) -> Path:
    return Path(state_dir) / STATE_FILE_NAME


def read_status(state_dir: str | Path, revision: str) -> BootstrapStatus:
    path = _state_path(state_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return BootstrapStatus(revision=revision, phase=BootstrapPhase.PENDING)
    except OSError, TypeError, ValueError:
        logger.warning("Could not read bootstrap state from %s", path, exc_info=True)
        return BootstrapStatus(revision=revision, phase=BootstrapPhase.PENDING)

    if not isinstance(data, dict) or data.get("revision") != revision:
        return BootstrapStatus(revision=revision, phase=BootstrapPhase.PENDING)

    try:
        phase = BootstrapPhase(data["phase"])
    except KeyError, TypeError, ValueError:
        logger.warning("Invalid bootstrap phase in %s: %r", path, data.get("phase"))
        return BootstrapStatus(revision=revision, phase=BootstrapPhase.PENDING)

    return BootstrapStatus(revision=revision, phase=phase)


def write_status(state_dir: str | Path, revision: str, phase: BootstrapPhase) -> None:
    directory = Path(state_dir)
    directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"revision": revision, "phase": phase.value})

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=directory,
            prefix=".state-",
            encoding="utf-8",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(_state_path(directory))
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def current_status() -> BootstrapStatus:
    return read_status(settings.BOOTSTRAP_STATE_DIR, settings.GIT_COMMIT_SHA)
