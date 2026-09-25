"""Peer eligibility rules driven by :class:`PeerRequirementsSettings`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from neuromancers_network.peers.models.settings import PeerRequirementsSettings

if TYPE_CHECKING:
    from neuromancers_network.users.models import User


def peer_requirements() -> PeerRequirementsSettings:
    """Return the admin-configured peer requirements (creating defaults)."""
    return PeerRequirementsSettings.load()


def eligibility_failures(user: User) -> list[str]:
    """Return the reasons *user* is not (yet) an eligible peer."""
    failures: list[str] = []

    profile = getattr(user, "peer_profile", None)
    if profile is None or not profile.is_approved:
        failures.append("not_approved")

    requirements = peer_requirements()
    payment = getattr(user, "payment_profile", None)

    if requirements.require_subscription and not (
        payment is not None and payment.has_active_subscription
    ):
        failures.append("no_active_subscription")

    if requirements.require_kyc and not (payment is not None and payment.kyc_completed):
        failures.append("kyc_incomplete")

    if requirements.require_verification_to_publish and not (
        profile is not None and profile.is_verified
    ):
        failures.append("not_verified")

    return failures


def is_eligible_peer(user: User | None) -> bool:
    """Whether *user* is approved and meets the configured peer requirements."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return not eligibility_failures(user)
