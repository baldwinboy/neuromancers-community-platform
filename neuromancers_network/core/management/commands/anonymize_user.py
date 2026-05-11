"""Anonymize a user's personal data for GDPR compliance.

Usage:
    python manage.py anonymize_user <user_id>

This command irreversibly anonymizes the specified user's personal data
while retaining aggregate/session data for platform integrity.
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Anonymize a user's personal data (GDPR data erasure)."

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=str, help="User ID or username to anonymize")

    def handle(self, *args, **options):
        identifier = options["user_id"]

        try:
            user = User.objects.get(
                models.Q(id=identifier) | models.Q(username=identifier),
            )
        except User.DoesNotExist:
            raise CommandError(f"User '{identifier}' not found.")

        anon_suffix = f"anon-{str(user.id)[:8]}"
        user.username = f"deleted-user-{anon_suffix}"
        user.email = f"deleted-{anon_suffix}@anonymized.invalid"
        user.first_name = ""
        user.last_name = ""
        user.date_of_birth = None
        user.is_active = False
        user.save(update_fields=[
            "username", "email", "first_name", "last_name",
            "date_of_birth", "is_active",
        ])

        self.stdout.write(self.style.SUCCESS(f"Anonymized user {identifier}"))
