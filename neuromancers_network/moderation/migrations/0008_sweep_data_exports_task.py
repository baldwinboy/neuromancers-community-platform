"""Schedule the data-export sweep task."""

from __future__ import annotations

from django.db import migrations

TASK = "neuromancers_network.moderation.tasks.sweep_data_exports"


def create_periodic_tasks(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    interval, _created = IntervalSchedule.objects.get_or_create(
        every=1,
        period="hours",
    )
    PeriodicTask.objects.update_or_create(
        name=TASK,
        defaults={"interval": interval, "task": TASK, "enabled": True},
    )


def delete_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0007_dataexportrequest_expires_at_and_more"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_periodic_tasks, delete_periodic_tasks),
    ]
