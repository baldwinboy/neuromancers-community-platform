from django.db import migrations
from ..utils import create_groups, delete_groups


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_create_homepage'),
    ]

    operations = [migrations.RunPython(create_groups, delete_groups)]
