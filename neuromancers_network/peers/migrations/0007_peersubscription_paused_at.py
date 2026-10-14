from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("peers", "0006_alter_peerapplicationformfield_input_design_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="peersubscription",
            name="paused_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Paused at",
            ),
        ),
    ]
