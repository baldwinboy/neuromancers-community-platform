"""Replace Review.is_published with Review.status (breaking column drop).

Forward: existing published rows become PUBLISHED, unpublished rows become
HIDDEN. Reverse: status PUBLISHED maps to is_published=True, everything else to
False. Deploy rollback requires restoring the pre-deploy database backup if the
data mapping must be preserved exactly (a hidden review cannot be distinguished
from a pending one once mapped back to the boolean).
"""

from __future__ import annotations

from django.db import migrations
from django.db import models


def forward(apps, schema_editor):
    Review = apps.get_model("meetings", "Review")
    Review.objects.filter(is_published=False).update(status="hidden")
    Review.objects.filter(is_published=True).update(status="published")


def reverse(apps, schema_editor):
    Review = apps.get_model("meetings", "Review")
    Review.objects.update(is_published=False)
    Review.objects.filter(status="published").update(is_published=True)


class Migration(migrations.Migration):
    dependencies = [
        ("meetings", "0012_meetingrequest_price_paid_base_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_approval", "Pending approval"),
                    ("published", "Published"),
                    ("hidden", "Hidden"),
                ],
                db_index=True,
                default="published",
                max_length=20,
                verbose_name="Status",
            ),
        ),
        migrations.RunPython(forward, reverse),
        migrations.RemoveField(
            model_name="review",
            name="is_published",
        ),
    ]
