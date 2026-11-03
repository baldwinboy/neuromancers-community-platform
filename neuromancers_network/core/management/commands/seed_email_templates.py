"""Seed allauth and notification email templates."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from neuromancers_network.core.email_seed import seed_email_templates


class Command(BaseCommand):
    help = "Seed allauth overrides and notification email templates (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing seeded email content.",
        )

    def handle(self, *args, **options):
        result = seed_email_templates(force=options["force"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Email templates seeded: {result['allauth']} allauth, "
                f"{result['events']} events.",
            ),
        )
