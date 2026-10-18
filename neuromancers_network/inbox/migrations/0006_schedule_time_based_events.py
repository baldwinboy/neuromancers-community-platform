from django.db import migrations

TASKS = [
    "neuromancers_network.inbox.tasks.emit_payment_reminders",
    "neuromancers_network.inbox.tasks.emit_session_reminders",
    "neuromancers_network.inbox.tasks.emit_upcoming_meetings",
]


def create_periodic_tasks(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    interval, _created = IntervalSchedule.objects.get_or_create(
        every=5,
        period="minutes",
    )
    for task in TASKS:
        PeriodicTask.objects.update_or_create(
            name=task,
            defaults={"interval": interval, "task": task, "enabled": True},
        )


def delete_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name__in=TASKS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inbox", "0005_alter_daisiebridgesubscriber_options"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_periodic_tasks, delete_periodic_tasks),
    ]
