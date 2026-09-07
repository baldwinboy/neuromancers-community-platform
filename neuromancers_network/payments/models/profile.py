from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from djstripe.enums import SubscriptionStatus

from neuromancers_network.core.models import Timestamped


class PaymentProfile(Timestamped):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_profile",
    )
    stripe_customer_id = models.OneToOneField(
        "djstripe.Customer",
        on_delete=models.CASCADE,
        related_name="payment_profile",
    )
    stripe_connect_account_id = models.OneToOneField(
        "djstripe.Account",
        on_delete=models.CASCADE,
        related_name="payment_profile",
    )
    kyc_completed = models.BooleanField(_("KYC completed"), default=False)

    @property
    def has_active_subscription(self) -> bool:
        """Whether the user currently subscribes to an active peer plan."""
        peer_subscription = getattr(self, "peer_subscription", None)
        if peer_subscription is None:
            return False
        return peer_subscription.subscription.status in (
            SubscriptionStatus.active,
            SubscriptionStatus.trialing,
        )
