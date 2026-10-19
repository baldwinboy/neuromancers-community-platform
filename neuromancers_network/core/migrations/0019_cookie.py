from __future__ import annotations

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0018_scriptssetting"),
    ]

    operations = [
        migrations.CreateModel(
            name="Cookie",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "name",
                    models.CharField(max_length=255, unique=True, verbose_name="Name"),
                ),
                (
                    "provider",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Provider",
                    ),
                ),
                ("purpose", models.TextField(blank=True, verbose_name="Purpose")),
                (
                    "duration",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        verbose_name="Duration",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("necessary", "Necessary"),
                            ("analytics", "Analytics"),
                            ("marketing", "Marketing"),
                        ],
                        db_index=True,
                        default="necessary",
                        max_length=20,
                        verbose_name="Category",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Active"),
                ),
            ],
            options={
                "verbose_name": "Cookie",
                "verbose_name_plural": "Cookies",
                "ordering": ["category", "name"],
            },
        ),
    ]
