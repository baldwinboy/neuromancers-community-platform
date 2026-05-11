"""Seed the Wagtail dashboard with initial Admin Guide topics.

Reads markdown source files from ``admin_guide/sources/`` and creates or
updates ``Guide`` instances.  After running this command,
admins can edit the guide content through the Wagtail CMS.

Usage::

    python manage.py bootstrap_admin_guide
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from neuromancers_network.admin_guide.models import Guide
from neuromancers_network.admin_guide.models import GuideTopic

GUIDE_DIR = Path(__file__).resolve().parent.parent.parent / "sources"

TOPICS = [
    {
        "slug": "wagtail-cms-admin-urls",
        "title": "Wagtail CMS Admin URLs",
        "summary":
        "Every /cms/ area an admin can use, what it does, and what can be changed there.",
        "file": "01-wagtail-cms-admin-urls.md",
    },
    {
        "slug": "static-urls-you-can-restyle",
        "title": "Static URLs You Can Restyle",
        "summary":
        "Front-end pages whose appearance and content can be edited through Wagtail.",
        "file": "02-static-urls-you-can-restyle.md",
    },
    {
        "slug": "site-settings-panels",
        "title": "Site Settings Panels",
        "summary":
        "All branding, email, security, terminology, navbar, footer, and auth settings panels.",
        "file": "03-site-settings-panels.md",
    },
    {
        "slug": "special-system-urls",
        "title": "Special System URLs",
        "summary":
        "System URLs admins should know about, even when they are not directly editable in Wagtail.",
        "file": "04-special-system-urls.md",
    },
]


class Command(BaseCommand):
    help = "Create or update Guide entries from markdown source files."

    def handle(self, *args, **options):
        default_topic, _ = GuideTopic.objects.get_or_create(
            title="General",
            defaults={"sort_order": 0},
        )

        for topic in TOPICS:
            source_path = GUIDE_DIR / topic["file"]
            try:
                raw_md = source_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                self.stderr.write(f"Missing: {source_path} — skipping.")
                continue

            guide, created = Guide.objects.update_or_create(
                slug=topic["slug"],
                defaults={
                    "title": topic["title"],
                    "summary": topic["summary"],
                    "topic": default_topic,
                    "content": [
                        ("paragraph", raw_md),
                    ],
                },
            )
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb}: {guide.title}"))
