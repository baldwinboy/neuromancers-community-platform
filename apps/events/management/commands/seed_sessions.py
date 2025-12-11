from django.core.management.base import BaseCommand

from apps.events.factories import (
    GroupSessionFactory,
    PeerSessionAvailabilityFactory,
    PeerSessionFactory,
)


class Command(BaseCommand):
    help = "Seeds the database with dummy users assigned to existing groups"

    def add_arguments(self, parser):
        parser.add_argument(
            "--size", type=int, default=100, help="Number of sessions to generate"
        )

    def handle(self, *args, **options):
        size = int(options["size"])

        GroupSessionFactory.create_batch(round(size / 2))
        PeerSessionAvailabilityFactory.create_batch(round(size / 4))
        PeerSessionFactory.create_batch(round(size / 4))

        self.stdout.write(self.style.SUCCESS("Done!"))
