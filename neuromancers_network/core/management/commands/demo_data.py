"""Manage deterministic demo/test data."""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from neuromancers_network.core.demo_data import DemoDataError
from neuromancers_network.core.demo_data import cleanup_demo_data
from neuromancers_network.core.demo_data import demo_data_status
from neuromancers_network.core.demo_data import seed_demo_data


class Command(BaseCommand):
    help = "Seed, inspect, or clean demo/test data."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["seed", "cleanup", "status"])
        parser.add_argument("--email", default="", help="Base email address.")
        parser.add_argument("--password", default="", help="Demo account password.")
        parser.add_argument(
            "--no-paused",
            action="store_true",
            help="Do not create the paused demo peer.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report cleanup changes without deleting.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm a real cleanup.",
        )

    def handle(self, *args, **options):
        action = options["action"]
        email = options["email"].strip()
        try:
            if action == "status":
                self._status(email)
            elif action == "seed":
                self._seed(options)
            else:
                self._cleanup(options)
        except DemoDataError as exc:
            raise CommandError(str(exc)) from exc

    def _status(self, email: str) -> None:
        status = demo_data_status(email or None)
        for key, value in status.items():
            self.stdout.write(f"{key}: {value}")

    def _seed(self, options) -> None:
        email = options["email"].strip()
        if not email:
            msg = "--email is required for seed."
            raise CommandError(msg)
        password = options["password"] or settings.DEMO_DATA_PASSWORD
        if not password:
            msg = "--password or DEMO_DATA_PASSWORD is required."
            raise CommandError(msg)
        result = seed_demo_data(
            email_base=email,
            password=password,
            include_paused_peer=not options["no_paused"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo data: "
                f"{result['users']} users, {result['meetings']} meetings.",
            ),
        )

    def _cleanup(self, options) -> None:
        email = options["email"].strip()
        if not email:
            msg = "--email is required for cleanup."
            raise CommandError(msg)
        if not options["dry_run"] and not options["yes"]:
            msg = "Pass --yes to delete demo data, or --dry-run."
            raise CommandError(msg)
        result = cleanup_demo_data(
            email_base=email,
            actor=None,
            dry_run=options["dry_run"],
        )
        for key, value in result.items():
            self.stdout.write(f"{key}: {value}")
