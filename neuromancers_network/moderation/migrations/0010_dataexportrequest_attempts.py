"""Track data-export build attempts so stale jobs can terminate."""

from __future__ import annotations

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0009_sweep_deleted_identities_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataexportrequest",
            name="attempts",
            field=models.PositiveIntegerField(default=0, verbose_name="Attempts"),
        ),
    ]
