from django.db import migrations

TASK = "neuromancers_network.meetings.tasks.mark_completed_sessions"


def create_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    interval, _created = IntervalSchedule.objects.get_or_create(
        every=5,
        period="minutes",
    )
    PeriodicTask.objects.update_or_create(
        name=TASK,
        defaults={"interval": interval, "task": TASK, "enabled": True},
    )


def delete_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=TASK).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "meetings",
            (
                "0008_remove_meeting_meetings_meeting_unique_published_title_"
                "per_peer_and_more"
            ),
        ),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, delete_periodic_task),
    ]
