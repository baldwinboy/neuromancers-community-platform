"""Deduplicate notifications and enforce one per recipient/event reference."""

from __future__ import annotations

from django.db import migrations
from django.db import models
from django.db.models import Count


def deduplicate_notifications(apps, schema_editor):
    Notification = apps.get_model("inbox", "Notification")
    duplicates = (
        Notification.objects.exclude(event_ref="")
        .values("recipient_id", "event_ref")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    for group in duplicates:
        rows = Notification.objects.filter(
            recipient_id=group["recipient_id"],
            event_ref=group["event_ref"],
        ).order_by("id")
        keep_id = rows.values_list("id", flat=True).first()
        rows.exclude(id=keep_id).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inbox", "0006_schedule_time_based_events"),
    ]

    operations = [
        migrations.RunPython(
            deduplicate_notifications,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.UniqueConstraint(
                fields=["recipient", "event_ref"],
                condition=~models.Q(event_ref=""),
                name="inbox_notif_recipient_event_ref_uniq",
            ),
        ),
    ]
