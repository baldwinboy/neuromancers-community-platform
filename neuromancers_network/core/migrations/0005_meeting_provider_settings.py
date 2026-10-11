from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_standardpagetag_standardpage_tags_tagindexpage_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="integrationsettings",
            old_name="whereby_room_prefix",
            new_name="meeting_room_prefix",
        ),
        migrations.AlterField(
            model_name="integrationsettings",
            name="meeting_room_prefix",
            field=models.CharField(
                default="neuromancers",
                help_text="Prefix for generated meeting room names.",
                max_length=50,
                verbose_name="Meeting room prefix",
            ),
        ),
        migrations.AddField(
            model_name="integrationsettings",
            name="meeting_provider",
            field=models.CharField(
                choices=[("whereby", "Whereby"), ("daily", "Daily.co")],
                default="whereby",
                help_text="Service used to generate meeting links for bookings.",
                max_length=20,
                verbose_name="Meeting provider",
            ),
        ),
        migrations.AddField(
            model_name="integrationsettings",
            name="daily_api_key",
            field=models.CharField(
                blank=True,
                help_text="API key for Daily.co integration.",
                max_length=255,
                verbose_name="Daily API Key",
            ),
        ),
    ]
