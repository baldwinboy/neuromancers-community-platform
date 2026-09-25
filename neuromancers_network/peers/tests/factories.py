from djstripe.enums import SubscriptionStatus

from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory


def make_peer(
    *,
    is_approved=True,
    is_verified=False,
    subscription_status=SubscriptionStatus.active,
    kyc_completed=True,
    default_terms="",
):
    """Build a user wired up with the full peer lifecycle state."""
    user = UserFactory()
    PeerProfileFactory(
        user=user,
        is_approved=is_approved,
        is_verified=is_verified,
        default_terms=default_terms,
    )
    payment_profile = PaymentProfileFactory(user=user, kyc_completed=kyc_completed)
    if subscription_status is not None:
        PeerSubscriptionFactory(
            payment_profile=payment_profile,
            subscription__status=subscription_status,
        )
    return user
