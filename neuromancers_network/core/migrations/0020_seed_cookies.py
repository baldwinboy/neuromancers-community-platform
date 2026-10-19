"""Seed the cookie registry with the cookies the site actually sets."""

from __future__ import annotations

from django.db import migrations

SEED_COOKIES = (
    (
        "django_language",
        "This site",
        "Remembers the language you selected.",
        "1 year",
        "necessary",
    ),
    (
        "daisie_theme",
        "This site",
        "Remembers your colour theme preference.",
        "1 year",
        "necessary",
    ),
    (
        "sessionid",
        "This site",
        "Keeps you signed in and protects your session.",
        "2 weeks",
        "necessary",
    ),
    (
        "csrftoken",
        "This site",
        "Protects forms against cross-site request forgery.",
        "1 year",
        "necessary",
    ),
)


def seed_cookies(apps, schema_editor):
    Cookie = apps.get_model("core", "Cookie")
    for name, provider, purpose, duration, category in SEED_COOKIES:
        Cookie.objects.get_or_create(
            name=name,
            defaults={
                "provider": provider,
                "purpose": purpose,
                "duration": duration,
                "category": category,
                "is_active": True,
            },
        )


def unseed_cookies(apps, schema_editor):
    Cookie = apps.get_model("core", "Cookie")
    Cookie.objects.filter(name__in=[row[0] for row in SEED_COOKIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0019_cookie"),
    ]

    operations = [
        migrations.RunPython(seed_cookies, unseed_cookies),
    ]
