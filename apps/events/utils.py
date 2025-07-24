# from django.contrib.auth.models import Group, Permission
# from django.contrib.auth.management import create_permissions

# GROUPS: list[str] = ["neuromancer", "peer", "support_seeker"]

# def create_groups(apps, schema_editor):
#     for group in GROUPS:
#         Group.objects.create(group)

#     # Permissions have to be created before applying them
#     for app_config in apps.get_app_configs():
#         app_config.models_module = True
#         create_permissions(app_config, verbosity=0)
#         app_config.models_module = None

#     all_perms = Permission.objects.all()
#     maintainer_perms = [i for i in all_perms if i.content_type.app_label == "batteryDB"]
#     Group.objects.get(name="Maintainer").permissions.add(*maintainer_perms)

# #     from django.db import migrations
# # from django.contrib.auth.models import Group

# # def create_groups(apps, schema_editor):
# #     Group.objects.create(name="neuromancer")
# #     Group.objects.create(name="peer")
# #     Group.objects.create(name="support_seeker")

# # def remove_groups(apps, schema_editor):
# #     Group.objects.filter(name__in=["neuromancer", "peer", "support_seeker"]).delete()

# # class Migration(migrations.Migration):

# #     initial = True

# #     dependencies = []

# #     operations = [
# #         migrations.RunPython(create_groups, remove_groups),
# #     ]

# def remove_groups(apps, schema_editor):
#     Group.objects.filter(name__in=GROUPS).delete()
