from djstripe.enums import SubscriptionStatus

from neuromancers_network.peers.models import PeerAvailability
from neuromancers_network.users.tests.factories import PaymentProfileFactory
from neuromancers_network.users.tests.factories import PeerProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory


def make_availability(  # noqa: PLR0913
    peer,
    *,
    start,
    end,
    occurrence="",
    occurrence_starts_at=None,
    occurrence_ends_at=None,
    reason="",
):
    """Create an availability window for *peer*."""
    return PeerAvailability.objects.create(
        peer=peer,
        start=start,
        end=end,
        occurrence=occurrence,
        occurrence_starts_at=occurrence_starts_at,
        occurrence_ends_at=occurrence_ends_at,
        reason=reason,
    )


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
