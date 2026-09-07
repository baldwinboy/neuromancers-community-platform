from django.db import models
from django.utils.translation import gettext_lazy as _


class SubscriptionInterval(models.TextChoices):
    MONTHLY = "month", _("Monthly")
    YEARLY = "year", _("Yearly")
