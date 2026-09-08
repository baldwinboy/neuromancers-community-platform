import logging

from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Account as StripeAccount

logger = logging.getLogger(__name__)


@djstripe_receiver("account.updated")
def handle_account_updated(sender, event, **kwargs):
    """Mark KYC complete when Stripe Connect onboarding is finished."""
    from neuromancers_network.payments.models import PaymentProfile  # noqa: PLC0415

    account_data = event.data.get("object", {})
    account_id = account_data.get("id")
    if not account_id:
        logger.warning("Ignoring account.updated without account id")
        return

    StripeAccount.sync_from_stripe_data(account_data, api_key=event.default_api_key)

    try:
        payment_profile = PaymentProfile.objects.get(
            stripe_connect_account_id_id=account_id,
        )
    except PaymentProfile.DoesNotExist:
        logger.warning("No payment profile found for connected account %s", account_id)
        return

    payment_profile.sync_kyc_completed_from_stripe_account(account_data)
