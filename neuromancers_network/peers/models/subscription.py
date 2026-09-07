from django.db import models

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
