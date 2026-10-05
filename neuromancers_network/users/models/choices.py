from django.db import models
from django.utils.translation import gettext_lazy as _


class StaffState(models.TextChoices):
    INACTIVE = "inactive", _("Inactive")
    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")


class ProfileVisibility(models.TextChoices):
    PUBLIC = "public", _("Public")
    MEMBERS = "members", _("Members only")
    PRIVATE = "private", _("Private")
