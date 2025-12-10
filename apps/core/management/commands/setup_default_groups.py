from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from guardian.shortcuts import assign_perm

from apps.accounts.models import UserGroup
from apps.events.models import (
    GroupSession,
    GroupSessionRequest,
    PeerScheduledSession,
    PeerSession,
    PeerSessionAvailability,
    PeerSessionRequest,
)


class Command(BaseCommand):
    help = "Sets up default groups and permissions for event session access with django-guardian"

    def handle(self, *args, **options):
        group_names = ["Support Seeker", "Peer", "Neuromancer"]
        groups = {
            name: UserGroup.objects.get_or_create(name=name)[0] for name in group_names
        }

        for name, group in groups.items():
            created = group._state.adding
            msg = (
                f"Created group: {name}" if created else f"Group already exists: {name}"
            )
            self.stdout.write(
                self.style.SUCCESS(msg) if created else self.style.WARNING(msg)
            )

        self.stdout.write(
            self.style.NOTICE("Adding default perms to default groups...")
        )

        # Common permissions across all groups
        base_perms = [
            ("events.view_peersession", PeerSession),
            ("events.request_session", PeerSession),
            ("events.view_peersessionavailability", PeerSessionAvailability),
            ("events.view_groupsession", GroupSession),
            ("events.request_join_session", GroupSession),
            ("events.add_peersessionrequest", PeerSessionRequest),
            ("events.add_groupsessionrequest", GroupSessionRequest),
        ]

        # Elevated Peer permissions
        peer_perms = [
            ("events.add_peersession", PeerSession),
            ("events.add_peerscheduledsession", PeerScheduledSession),
            ("events.add_peersessionavailability", PeerSessionAvailability),
            ("events.add_groupsession", GroupSession),
        ]

        # Neuromancer: assign all permissions for specific models
        neuromancer_models = [
            PeerSession,
            PeerSessionAvailability,
            PeerSessionRequest,
            PeerScheduledSession,
            GroupSession,
            GroupSessionRequest,
        ]

        for group_name, group in groups.items():
            self.stdout.write(
                self.style.NOTICE(f"Assigning perms to `{group_name}` group...")
            )

            # Assign base perms
            for codename, model in base_perms:
                assign_perm(codename, group)
                self.stdout.write(
                    self.style.SUCCESS(f"Assigned {codename} to {group_name}")
                )

            # Assign peer perms
            if group_name == "Peer":
                for codename, model in peer_perms:
                    assign_perm(codename, group)
                    self.stdout.write(
                        self.style.SUCCESS(f"Assigned {codename} to {group_name}")
                    )

            # Assign all perms to Neuromancer
            if group_name == "Neuromancer":
                for model in neuromancer_models:
                    content_type = ContentType.objects.get_for_model(model)
                    perms = Permission.objects.filter(content_type=content_type)
                    self.stdout.write(
                        self.style.NOTICE(f"Found content type for {model.__name__}")
                    )

                    for perm in perms:
                        assign_perm(
                            f"{perm.content_type.app_label}.{perm.codename}", group
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Assigned {perm.codename} to {group_name}"
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS("Default groups and permissions have been set up.")
        )
