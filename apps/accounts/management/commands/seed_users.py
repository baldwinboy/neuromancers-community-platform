from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.accounts.factories import UserFactory


class Command(BaseCommand):
    help = "Seeds the database with dummy users assigned to existing groups"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users", type=int, default=50, help="Number of users to generate"
        )
        parser.add_argument(
            "--group",
            type=str,
            default=None,
            help="Group name to assign users to (e.g. 'Peer', 'Support Seeker')",
        )
        parser.add_argument(
            "--groups",
            nargs="+",
            type=str,
            default=None,
            help='Multiple group names to assign (e.g. --groups \'"Peer","Support Seeker"\')',
        )

    def handle(self, *args, **options):
        num_users = options["users"]
        single_group = options["group"]
        multiple_groups = options["groups"]

        # Resolve groups
        if single_group:
            groups_to_assign = [single_group]
        elif multiple_groups:
            groups_to_assign = [
                g.strip() for g in multiple_groups[0].split(",") if g.strip()
            ]

        else:
            raise ValueError("You must specify --group or --groups")

        # Validate groups exist
        for group_name in groups_to_assign:
            if not Group.objects.filter(name=group_name).exists():
                raise ValueError(f"Group does not exist: {group_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Creating {num_users} users with groups: {groups_to_assign}"
            )
        )

        for _ in range(num_users):
            UserFactory(groups=groups_to_assign)

        self.stdout.write(self.style.SUCCESS("Done!"))
