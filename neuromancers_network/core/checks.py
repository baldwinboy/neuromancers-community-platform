"""System checks for encrypted integration secrets."""

from __future__ import annotations

from django.core.checks import Error
from django.core.checks import register
from django.db import DatabaseError
from django.db import connection

SECRET_FIELDS = {
    "StripeSettings": ("secret_key", "webhook_secret", "client_id"),
    "EmailSettings": ("password",),
    "IntegrationSettings": (
        "getpronto_api_key",
        "whereby_api_key",
        "daily_api_key",
        "whereby_webhook_secret",
        "daily_webhook_secret",
    ),
}


@register()
def check_secret_decryption(app_configs, **kwargs):
    from neuromancers_network.core.crypto import SecretDecryptionError  # noqa: PLC0415
    from neuromancers_network.core.crypto import decrypt  # noqa: PLC0415
    from neuromancers_network.core.models import EmailSettings  # noqa: PLC0415
    from neuromancers_network.core.models import IntegrationSettings  # noqa: PLC0415
    from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415

    models = (StripeSettings, EmailSettings, IntegrationSettings)
    errors = []
    for model in models:
        fields = SECRET_FIELDS[model.__name__]
        columns = ", ".join(["id", *fields])
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT {columns} FROM {model._meta.db_table}",  # noqa: S608, SLF001
                )
                rows = cursor.fetchall()
        except DatabaseError:
            continue
        for row in rows:
            pk, *values = row
            for name, value in zip(fields, values, strict=True):
                try:
                    decrypt(value)
                except SecretDecryptionError as exc:
                    errors.append(
                        Error(
                            f"{model.__name__}.{name} (pk={pk}): {exc}",
                            id="core.E001",
                        ),
                    )
    return errors
