from dataclasses import dataclass
from typing import TYPE_CHECKING

import stripe
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from djstripe.enums import SubscriptionStatus

from neuromancers_network.core.models import Timestamped

if TYPE_CHECKING:
    from djstripe.models import Account as StripeAccount


@dataclass(frozen=True)
class StripeConnectOnboardingLink:
    account_id: str
    url: str


class PaymentProfile(Timestamped):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_profile",
    )
    stripe_customer_id = models.OneToOneField(
        "djstripe.Customer",
        on_delete=models.CASCADE,
        to_field="id",
        related_name="payment_profile",
    )
    stripe_connect_account_id = models.OneToOneField(
        "djstripe.Account",
        on_delete=models.CASCADE,
        to_field="id",
        related_name="payment_profile",
        null=True,
        blank=True,
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

    def create_stripe_onboarding_link(
        self,
        *,
        refresh_url: str,
        return_url: str,
    ) -> StripeConnectOnboardingLink:
        from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415
        from neuromancers_network.payments.services import (  # noqa: PLC0415
            ensure_stripe_account,
        )

        stripe_settings = StripeSettings.load()
        if not stripe_settings.secret_key:
            error_message = "Stripe secret key is not configured"
            raise ValueError(error_message)

        ensure_stripe_account(self.user)
        self.refresh_from_db()
        account_id = self.stripe_connect_account_id_id  # type: ignore[attr-defined]

        stripe.api_key = stripe_settings.secret_key
        link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )
        return StripeConnectOnboardingLink(account_id=str(account_id), url=link.url)

    def create_express_dashboard_link(self) -> str:
        from neuromancers_network.core.models import StripeSettings  # noqa: PLC0415

        stripe_settings = StripeSettings.load()
        if not stripe_settings.secret_key:
            error_message = "Stripe secret key is not configured"
            raise ValueError(error_message)

        account_id = self.stripe_connect_account_id_id  # type: ignore[attr-defined]
        if not account_id:
            error_message = "Payment profile has no connected Stripe account"
            raise ValueError(error_message)

        stripe.api_key = stripe_settings.secret_key
        link = stripe.Account.create_login_link(account_id)
        return link.url

    def sync_kyc_completed_from_stripe_account(
        self,
        stripe_account: StripeAccount,
    ) -> bool:
        requirements = getattr(stripe_account, "requirements", None)
        if isinstance(stripe_account, dict):
            requirements = stripe_account.get("requirements") or {}
            charges_enabled = bool(stripe_account.get("charges_enabled"))
            payouts_enabled = bool(stripe_account.get("payouts_enabled"))
            details_submitted = bool(stripe_account.get("details_submitted"))
        else:
            charges_enabled = bool(getattr(stripe_account, "charges_enabled", False))
            payouts_enabled = bool(getattr(stripe_account, "payouts_enabled", False))
            details_submitted = bool(
                getattr(stripe_account, "details_submitted", False),
            )
            requirements = requirements or {}

        currently_due = list(getattr(requirements, "currently_due", []) or [])
        eventually_due = list(getattr(requirements, "eventually_due", []) or [])
        past_due = list(getattr(requirements, "past_due", []) or [])

        completed = bool(
            details_submitted
            and charges_enabled
            and payouts_enabled
            and not currently_due
            and not eventually_due
            and not past_due,
        )
        if self.kyc_completed != completed:
            self.kyc_completed = completed
            self.save(update_fields=["kyc_completed", "updated_at"])
        return self.kyc_completed
