"""Schedule the account-deletion purge task."""

from __future__ import annotations

from django.db import migrations

TASK = "neuromancers_network.moderation.tasks.purge_due_account_deletions"


def create_periodic_tasks(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    interval, _created = IntervalSchedule.objects.get_or_create(
        every=1,
        period="days",
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
        ("moderation", "0005_alter_supportformfield_input_design_and_more"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_periodic_tasks, delete_periodic_tasks),
    ]
