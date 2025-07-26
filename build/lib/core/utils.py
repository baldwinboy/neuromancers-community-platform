from collections import namedtuple

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission

DefaultGroups = namedtuple("DefaultGroups", ["NEUROMANCER", "PEER", "SUPPORT_SEEKER"])
groups = DefaultGroups("Neuromancer", "Peer", "Support Seeker")


def create_groups(apps, schema_editor):
    """
    Create default groups for platform with permissions
    """
    for group in groups:
        Group.objects.get_or_create(name=group)

    # Permissions have to be created before applying them
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, verbosity=0)
        app_config.models_module = None

    all_perms = Permission.objects.all()
    Group.objects.get(name=groups.NEUROMANCER).permissions.add(*all_perms)


def delete_groups(apps, schema_editor):
    """
    Delete default groups
    """
    Group.objects.filter(name__in=groups).delete()
