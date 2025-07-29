import json

from django.conf import settings
from django.db import models


class SessionRequestStatusChoices(models.IntegerChoices):
    """
    Session requests may be approved, rejected, or left pending
    """

    APPROVED = 0, "Approved"
    REJECTED = 1, "Rejected"
    PENDING = 2, "Pending"


class SessionAvailabilityOccurrenceChoices(models.IntegerChoices):
    """
    Session availability may occur hourly, daily, weekly, monthly, or yearly
    """

    HOURLY = 0, "Hourly"
    DAILY = 1, "Daily"
    WEEKLY = 2, "Weekly"
    MONTHLY = 3, "Monthly"
    YEARLY = 4, "Yearly"


# Create currency choices
with open(settings.STRIPE_CURRENCIES) as f:
    # Stripe only allows certain currencies
    STRIPE_CURRENCIES = set(line.strip().upper() for line in f if line.strip())

with open(settings.CURRENCIES) as f:
    # Ideal complete list of currencies with details
    CURRENCIES = json.load(f)

# Filter currencies
filtered_currencies = {
    iso: details for iso, details in CURRENCIES.items() if iso in STRIPE_CURRENCIES
}

currency_choices = [
    (iso, f"{details['name']} ({details['symbol']})")
    for iso, details in filtered_currencies.items()
]
