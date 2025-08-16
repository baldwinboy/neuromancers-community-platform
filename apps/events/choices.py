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


class SessionAvailabilityOccurrenceChoices(models.IntegerChoices):
    """
    Session availability may occur hourly, daily, weekly, monthly, or yearly
    """

    HOURLY = 0, _("Hourly")
    DAILY = 1, _("Daily")
    WEEKLY = 2, _("Weekly")
    MONTHLY = 3, _("Monthly")
    YEARLY = 4, _("Yearly")


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
