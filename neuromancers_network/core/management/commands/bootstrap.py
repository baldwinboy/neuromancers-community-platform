"""Run production bootstrap work outside the web container."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.management import BaseCommand
from django.core.management import call_command

from neuromancers_network.core.bootstrap_state import BootstrapPhase
from neuromancers_network.core.bootstrap_state import write_status

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Apply migrations, ensure the superuser, and seed code-owned content."

    state_dir: Path
    revision: str

    def handle(self, *args, **options) -> None:
        self.state_dir = Path(settings.BOOTSTRAP_STATE_DIR)
        self.revision = settings.GIT_COMMIT_SHA

        self._run_phase(
            BootstrapPhase.MIGRATING,
            BootstrapPhase.FAILED_MIGRATE,
            lambda: call_command("migrate", interactive=False),
        )
        self._run_phase(
            BootstrapPhase.SEEDING,
            BootstrapPhase.FAILED_BOOTSTRAP,
            self._seed,
        )
        write_status(self.state_dir, self.revision, BootstrapPhase.COMPLETE)
        self.stdout.write(self.style.SUCCESS("Bootstrap complete."))

    def _seed(self) -> None:
        call_command("ensure_superuser")
        call_command("seed_help_guide", force=True)
        call_command("seed_pages")
        call_command("seed_account_selfservice", force=True)

    def _run_phase(
        self,
        phase: BootstrapPhase,
        failure_phase: BootstrapPhase,
        action: Callable[[], None],
    ) -> None:
        write_status(self.state_dir, self.revision, phase)
        self.stdout.write(f"Bootstrap phase: {phase.value}")
        try:
            action()
        except Exception:
            logger.exception("Bootstrap failed during %s", phase.value)
            try:
                write_status(self.state_dir, self.revision, failure_phase)
            except OSError:
                logger.exception("Could not persist bootstrap failure state")
            raise
