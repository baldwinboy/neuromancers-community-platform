from django.core.management.base import BaseCommand

from apps.core.models import HomePage
from apps.events.models_pages.wagtail_pages import SessionsIndexPage


class Command(BaseCommand):
    help = "Publish all unpublished SessionsIndexPages"

    def handle(self, *args, **options):
        try:
            root = HomePage.objects.get(live=True)
        except HomePage.DoesNotExist:
            raise RuntimeError(
                "Homepage does not exist yet. Run homepage migration first."
            )

        index_pages = SessionsIndexPage.objects.all()

        for page in index_pages:
            if not page.live:
                revision = page.save_revision()
                revision.publish()
                self.stdout.write(f"Published: {page.title}")
            page.move(root, "right")
        if not index_pages.exists():
            self.stdout.write("No unpublished SessionsIndexPages found.")
