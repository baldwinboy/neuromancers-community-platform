"""Drop the unused price-tier default flag (options carry the default)."""

from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("meetings", "0009_schedule_mark_completed_sessions"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="meetingpricetier",
            name="is_default",
        ),
    ]
