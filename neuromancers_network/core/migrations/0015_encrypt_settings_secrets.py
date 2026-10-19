"""Encrypt existing integration secrets at rest.

Forward-only: the reverse is a no-op because the plaintext values are not kept.
Roll back by restoring the database backup taken before the deploy; see
``docs/infra/secrets-runbook.md``.
"""

from __future__ import annotations

from django.db import migrations

SECRET_FIELDS = {
    "StripeSettings": ("secret_key", "webhook_secret", "client_id"),
    "EmailSettings": ("password",),
    "IntegrationSettings": (
        "getpronto_api_key",
        "whereby_api_key",
        "daily_api_key",
    ),
}


def encrypt_existing_secrets(apps, schema_editor):
    from neuromancers_network.core.crypto import encrypt  # noqa: PLC0415
    from neuromancers_network.core.crypto import is_encrypted  # noqa: PLC0415

    for model_name, field_names in SECRET_FIELDS.items():
        model = apps.get_model("core", model_name)
        for row in model.objects.all().iterator():
            updates = {}
            for name in field_names:
                value = getattr(row, name)
                if value and not is_encrypted(value):
                    updates[name] = encrypt(value)
            if updates:
                model.objects.filter(pk=row.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_alter_emailsettings_password_and_more"),
    ]

    operations = [
        migrations.RunPython(
            encrypt_existing_secrets,
            migrations.RunPython.noop,
        ),
    ]
