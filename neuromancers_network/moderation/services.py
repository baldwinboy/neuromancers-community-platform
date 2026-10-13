"""Account deletion lifecycle: request, cancel and purge (anonymise)."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from neuromancers_network.core.audit import record_audit
from neuromancers_network.inbox.events import emit
from neuromancers_network.inbox.payloads import account_lifecycle_payload
from neuromancers_network.users.services import deactivate_account
from neuromancers_network.users.services import reactivate_account

from .identity import record_deleted_identity
from .models import AccountDeletionRequest
from .models import DeletionStatus

logger = logging.getLogger(__name__)

DEFAULT_GRACE_DAYS = 14
DEFAULT_REREGISTRATION_DAYS = 180


def _account_settings():
    from neuromancers_network.core.models import AccountSettings  # noqa: PLC0415

    try:
        return AccountSettings.load()
    except Exception:  # noqa: BLE001 - settings table may not exist yet
        return None


def _grace_days() -> int:
    return int(
        getattr(_account_settings(), "account_deletion_grace_days", DEFAULT_GRACE_DAYS)
        or 0,
    )


def _reregistration_days() -> int:
    return int(
        getattr(
            _account_settings(),
            "reregistration_cooldown_days",
            DEFAULT_REREGISTRATION_DAYS,
        )
        or 0,
    )


def _announce(  # noqa: PLR0913
    event_type: str,
    action: str,
    user,
    *,
    actor=None,
    request=None,
    reason: str = "",
    scheduled_for=None,
) -> None:
    try:
        emit(
            event_type,
            payload=account_lifecycle_payload(
                user,
                actor=actor,
                recipients=[user],
                reason=reason,
                deletion_scheduled_for=scheduled_for,
            ),
            event_ref=f"user.{user.pk}.{event_type}.{timezone.now().isoformat()}",
        )
    except Exception:
        logger.exception("Failed to emit %s for user %s", event_type, user.pk)
    try:
        record_audit(
            action=action,
            actor=actor,
            user=user,
            request=request,
            event_type=event_type,
            reason=reason,
        )
    except Exception:
        logger.exception("Failed to audit %s for user %s", action, user.pk)


def request_account_deletion(
    user,
    *,
    actor=None,
    request=None,
    reason: str = "",
) -> AccountDeletionRequest:
    """Schedule deletion after the grace period and deactivate the account."""
    scheduled_for = timezone.now() + timedelta(days=_grace_days())
    deletion, _created = AccountDeletionRequest.objects.update_or_create(
        user=user,
        defaults={
            "requested_by": actor,
            "reason": reason or "",
            "status": DeletionStatus.PENDING,
            "scheduled_for": scheduled_for,
            "completed_at": None,
        },
    )
    deactivate_account(
        user,
        actor=actor,
        request=request,
        reason=reason or "Account deletion requested",
    )
    _announce(
        "account_deletion_scheduled",
        "account.deletion.request",
        user,
        actor=actor,
        request=request,
        reason=reason,
        scheduled_for=scheduled_for,
    )
    return deletion


def cancel_account_deletion(user, *, actor=None, request=None) -> None:
    """Cancel a pending deletion and reactivate the account."""
    deletion = AccountDeletionRequest.objects.filter(
        user=user,
        status=DeletionStatus.PENDING,
    ).first()
    if deletion is None:
        return

    deletion.status = DeletionStatus.CANCELLED
    deletion.save(update_fields=["status", "updated_at"])
    reactivate_account(user, actor=actor, request=request)
    _announce(
        "account_deletion_cancelled",
        "account.deletion.cancel",
        user,
        actor=actor,
        request=request,
    )


def _disconnect_stripe(user) -> None:
    profile = getattr(user, "payment_profile", None)
    if profile is None or not profile.stripe_connect_account_id_id:
        return
    from neuromancers_network.payments.services import (  # noqa: PLC0415
        disconnect_stripe_account,
    )

    try:
        disconnect_stripe_account(profile)
    except Exception:
        logger.exception("Failed to disconnect Stripe for user %s", user.pk)


def _anonymize(user) -> None:
    """Erase direct identifiers, keeping the row for financial records."""
    user.username = f"deleted-{user.pk}"
    user.email = f"deleted-{user.pk}@deleted.invalid"
    user.name = ""
    user.date_of_birth = None
    user.accepted_tos = False
    user.is_active = False
    user.save(
        update_fields=[
            "username",
            "email",
            "name",
            "date_of_birth",
            "accepted_tos",
            "is_active",
        ],
    )

    # allauth stores verified addresses separately; clear them too.
    user.emailaddress_set.all().delete()

    profile = getattr(user, "user_profile", None)
    if profile is not None:
        profile.access_needs = ""
        profile.access_needs_templates = []
        profile.profile_picture_url = ""
        profile.profile_picture_getpronto_id = ""
        profile.save(
            update_fields=[
                "access_needs",
                "access_needs_templates",
                "profile_picture_url",
                "profile_picture_getpronto_id",
                "updated_at",
            ],
        )

    peer_profile = getattr(user, "peer_profile", None)
    if peer_profile is not None:
        peer_profile.bio = ""
        peer_profile.default_terms = ""
        peer_profile.save(update_fields=["bio", "default_terms", "updated_at"])


def purge_account(user, *, actor=None, request=None) -> None:
    """Anonymise *user* now, record a re-registration cooldown and audit it."""
    original_email = user.email
    original_username = user.username

    if user.is_active:
        deactivate_account(
            user,
            actor=actor,
            request=request,
            reason="Account deleted",
        )

    _disconnect_stripe(user)
    _anonymize(user)
    record_deleted_identity(
        email=original_email,
        username=original_username,
        cooldown_days=_reregistration_days(),
    )

    deletion = AccountDeletionRequest.objects.filter(user=user).first()
    if deletion is not None:
        deletion.status = DeletionStatus.COMPLETED
        deletion.completed_at = timezone.now()
        deletion.save(update_fields=["status", "completed_at", "updated_at"])

    _announce(
        "account_deleted",
        "account.deletion.purge",
        user,
        actor=actor,
        request=request,
    )


def purge_due_accounts(now=None) -> int:
    """Purge every pending deletion whose grace window has elapsed."""
    now = now or timezone.now()
    due = AccountDeletionRequest.objects.filter(
        status=DeletionStatus.PENDING,
        scheduled_for__lte=now,
    ).select_related("user")
    purged = 0
    for deletion in due:
        purge_account(deletion.user)
        purged += 1
    return purged
