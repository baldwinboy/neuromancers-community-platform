from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils.translation import gettext as _


class UserGroupPermissionsMixin(PermissionsMixin):
    groups = models.ManyToManyField(
        "UserGroup",
        verbose_name=_("groups"),
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="user_set",
        related_query_name="user",
    )


class Meta(PermissionsMixin.Meta):
    abstract = True
