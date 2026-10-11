from django.db import models
from django.utils.translation import gettext_lazy as _


class PeerApplicationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")


class AvailabilityOccurrence(models.TextChoices):
    NONE = "", _("Does not repeat")
    DAILY = "daily", _("Daily")
    WEEKLY = "weekly", _("Weekly")
    MONTHLY = "monthly", _("Monthly")


class CalendarEventKind(models.TextChoices):
    AVAILABLE = "available", _("Available")
    ONE_TO_ONE = "one_to_one", _("1:1 meeting")
    GROUP = "group", _("Group meeting")
