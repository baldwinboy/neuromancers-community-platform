from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _


class SessionRequestStatusChoices(models.IntegerChoices):
    """
    Session requests may be approved, rejected, or left pending
    """

    APPROVED = 0, _("Approved")
    REJECTED = 1, _("Rejected")
    PENDING = 2, _("Pending")
    WITHDRAWN = 3, _("Withdrawn")


class SessionAvailabilityOccurrenceChoices(models.IntegerChoices):
    """
    Session availability may occur daily, weekly, or monthly
    """

    DAILY = 0, _("Daily")
    WEEKLY = 1, _("Weekly")
    MONTHLY = 2, _("Monthly")


class GroupSessionOccurrenceChoices(models.IntegerChoices):
    """
    Group sessions may occur daily, weekly, every two weeks, every three weeks, or monthly
    """

    DAILY = 0, _("Daily")
    WEEKLY = 1, _("Weekly")
    FORTNIGHTLY = 2, _("Every two weeks")
    EVERY_3_WEEKS = 3, _("Every three weeks")
    MONTHLY = 4, _("Monthly")


# Filter currencies
filtered_currencies = {
    iso: details
    for iso, details in settings.CURRENCIES.items()
    if iso in settings.STRIPE_CURRENCIES
}

currency_choices = [
    (iso, f"{details['name']} ({details['symbol']})")
    for iso, details in filtered_currencies.items()
]
