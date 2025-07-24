from django.contrib.auth.models import AbstractUser
from django.db import models


# Users
# These are models that control users with specific groups
# Wagtail has a default management interface through the admin site: Settings > Users
# But this means creating the users for specific groups required every time the database is cleared
# Programmatic user types will allow for users with specific groups to be initialised wherever the project is deployed
class User(AbstractUser):
    display_picture = models.ImageField(
        help_text="This image will be displayed on a user's profile"
    )
    profile_bio = models.TextField(
        help_text="This will be displayed on a user's profile as their summary"
    )

    def __str__(self):
        return self.username
