"""Ensure an initial superuser exists, sourced from environment variables."""

from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from neuromancers_network.users.services import sync_email_address
from neuromancers_network.users.utils import normalize_email
from neuromancers_network.users.utils import normalize_username


class Command(BaseCommand):
    help = (
        "Create the initial superuser from DJANGO_SUPERUSER_USERNAME, "
        "DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD when no "
        "superuser exists. Safe to run on every deployment."
    )

    def handle(self, *args, **options):
        user_model = get_user_model()
        if user_model.objects.filter(is_superuser=True).exists():
            self.stdout.write("A superuser already exists; nothing to do.")
            return

        username = normalize_username(
            os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip(),
        )
        email = normalize_email(
            os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip(),
        )
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not username or not password:
            self.stdout.write(
                "DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD are "
                "not set; skipping superuser creation.",
            )
            return

        user, _ = user_model.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )
        user.email = email or user.email
        user.is_superuser = True
        user.is_staff = True
        user.set_password(password)
        user.save()
        self._ensure_verified_email(user)
        self.stdout.write(
            self.style.SUCCESS(f"Created superuser {username!r}."),
        )

    def _ensure_verified_email(self, user) -> None:
        address = sync_email_address(user)
        if address is None:
            return

        if not address.set_verified():
            self.stderr.write(
                f"Could not verify {address.email!r}: it is already verified "
                "for another account.",
            )
        address.set_as_primary()
