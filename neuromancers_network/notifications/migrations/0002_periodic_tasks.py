from django.db import migrations


def create_periodic_tasks(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    interval, _created = IntervalSchedule.objects.get_or_create(
        every=1,
        period="hours",
    )

    tasks = [
        "neuromancers_network.notifications.tasks.emit_payment_reminders",
        "neuromancers_network.notifications.tasks.emit_upcoming_meetings",
    ]

    for task_name in tasks:
        PeriodicTask.objects.update_or_create(
            name=task_name,
            defaults={
                "interval": interval,
                "task": task_name,
                "enabled": True,
            },
        )


def delete_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        name__in=[
            "neuromancers_network.notifications.tasks.emit_payment_reminders",
            "neuromancers_network.notifications.tasks.emit_upcoming_meetings",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_periodic_tasks, delete_periodic_tasks),
    ]
