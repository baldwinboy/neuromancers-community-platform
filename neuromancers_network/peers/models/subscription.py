from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models import Timestamped


class PeerSubscription(Timestamped):
    payment_profile = models.OneToOneField(
        "payments.PaymentProfile",
        on_delete=models.CASCADE,
        related_name="peer_subscription",
    )
    subscription = models.OneToOneField(
        "djstripe.Subscription",
        on_delete=models.CASCADE,
        related_name="peer_subscription",
    )
    paused_at = models.DateTimeField(_("Paused at"), null=True, blank=True)

    @property
    def is_paused(self) -> bool:
        """Whether collection is paused (a pause leaves the status unchanged)."""
        return self.paused_at is not None
