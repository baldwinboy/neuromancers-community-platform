from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meetings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="meeting",
            name="refund_requires_approval",
            field=models.BooleanField(default=True, verbose_name="Refund requires approval"),
        ),
        migrations.AddField(
            model_name="refundrequest",
            name="stripe_refund_id",
            field=models.CharField(blank=True, max_length=255, verbose_name="Stripe refund ID"),
        ),
    ]
