"""Block Celery startup until the production bootstrap completes."""

from __future__ import annotations

import time

from django.conf import settings
from django.core.management import BaseCommand

from neuromancers_network.core.bootstrap_state import BootstrapPhase
from neuromancers_network.core.bootstrap_state import current_status

POLL_INTERVAL_SECONDS = 2.0
LOG_INTERVAL_SECONDS = 30.0


class Command(BaseCommand):
    help = "Block Celery startup until the production bootstrap completes."

    def handle(self, *args, **options) -> None:
        if not settings.BOOTSTRAP_GATE_ENABLED:
            return

        last_phase: BootstrapPhase | None = None
        last_log = 0.0
        while True:
            status = current_status()
            if status.phase is BootstrapPhase.COMPLETE:
                self.stdout.write(
                    self.style.SUCCESS("Bootstrap complete; starting Celery."),
                )
                return

            now = time.monotonic()
            if status.phase is not last_phase or now - last_log >= LOG_INTERVAL_SECONDS:
                self.stderr.write(
                    "Waiting for bootstrap "
                    f"(phase={status.phase.value}, revision={status.revision}).",
                )
                last_phase = status.phase
                last_log = now

            time.sleep(POLL_INTERVAL_SECONDS)
