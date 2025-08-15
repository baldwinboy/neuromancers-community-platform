from django.core.management.base import BaseCommand

from apps.events.models_pages.wagtail_pages import SessionsIndexPage


class Command(BaseCommand):
    help = "Publish all unpublished SessionsIndexPages"

    def handle(self, *args, **options):
        unpublished = SessionsIndexPage.objects.filter(live=False)
        for page in unpublished:
            revision = page.save_revision()
            revision.publish()
            self.stdout.write(f"Published: {page.title}")
        if not unpublished.exists():
            self.stdout.write("No unpublished SessionsIndexPages found.")
