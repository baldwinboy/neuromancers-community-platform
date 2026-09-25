from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel

from neuromancers_network.core.models.base import Timestamped

from .meeting import MAX_DURATION_MINUTES
from .meeting import MIN_DURATION_MINUTES


class MeetingPriceTier(ClusterableModel):
    """A duration-based price tier for a meeting (e.g. 30/60 minutes)."""

    meeting = models.ForeignKey(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="price_tiers",
    )
    duration_minutes = models.PositiveIntegerField(
        _("Duration (minutes)"),
        validators=[
            MinValueValidator(MIN_DURATION_MINUTES),
            MaxValueValidator(MAX_DURATION_MINUTES),
        ],
    )
    is_default = models.BooleanField(_("Default tier"), default=False)

    class Meta:
        ordering = ["duration_minutes"]
        verbose_name = _("Price tier")
        verbose_name_plural = _("Price tiers")
        constraints = [
            models.UniqueConstraint(
                fields=["meeting", "duration_minutes"],
                name="%(app_label)s_%(class)s_unique_duration",
            ),
        ]

    def __str__(self):
        return f"{self.meeting} — {self.duration_minutes} min"


class MeetingPriceOption(Timestamped):
    """A selectable price within a tier (e.g. sliding-scale options)."""

    tier = ParentalKey(
        MeetingPriceTier,
        on_delete=models.CASCADE,
        related_name="options",
    )
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2)
    label = models.CharField(_("Label"), max_length=100, blank=True)
    is_default = models.BooleanField(_("Default option"), default=False)

    class Meta:
        ordering = ["-is_default", "amount"]
        verbose_name = _("Price option")
        verbose_name_plural = _("Price options")

    def __str__(self):
        return self.label or str(self.amount)
