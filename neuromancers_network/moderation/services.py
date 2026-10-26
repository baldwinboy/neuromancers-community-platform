"""Account deletion lifecycle: request, cancel and purge (anonymise)."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from neuromancers_network.core.audit import record_audit
from neuromancers_network.inbox.events import emit
from neuromancers_network.inbox.payloads import account_lifecycle_payload
from neuromancers_network.users.services import deactivate_account
from neuromancers_network.users.services import reactivate_account

from .identity import record_deleted_identity
from .models import AccountDeletionRequest
from .models import DeletionStatus
from .tokens import deletion_cancel_url

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
    cancel_url: str = "",
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
                deletion_cancel_url=cancel_url,
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
        cancel_url=deletion_cancel_url(deletion, request=request),
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


def send_deletion_cancel_email(
    deletion,
    *,
    actor=None,
    request=None,
) -> bool:
    """Resend the signed cancellation link for a pending deletion."""
    if deletion.status != DeletionStatus.PENDING:
        return False
    _announce(
        "account_deletion_scheduled",
        "account.deletion.resend",
        deletion.user,
        actor=actor,
        request=request,
        scheduled_for=deletion.scheduled_for,
        cancel_url=deletion_cancel_url(deletion, request=request),
    )
    return True


def _cancel_stripe_subscription(user) -> None:
    """Cancel the peer's platform subscription before the account is erased."""
    profile = getattr(user, "payment_profile", None)
    if profile is None:
        return
    peer_subscription = getattr(profile, "peer_subscription", None)
    if peer_subscription is None or not peer_subscription.subscription_id:
        return
    from neuromancers_network.payments.services import cancel_subscription  # noqa: PLC0415

    try:
        cancel_subscription(profile, at_period_end=False)
    except Exception:
        logger.exception("Failed to cancel Stripe subscription for user %s", user.pk)


def _disconnect_stripe(user) -> None:
    profile = getattr(user, "payment_profile", None)
    if profile is None or not profile.stripe_connect_account_id_id:
        return
    from neuromancers_network.payments.services import disconnect_stripe_account  # noqa: PLC0415

    try:
        disconnect_stripe_account(profile)
    except Exception:
        logger.exception("Failed to disconnect Stripe for user %s", user.pk)


def _anonymize(user) -> None:
    """Erase direct identifiers and privilege, keeping the row for records."""
    from neuromancers_network.users.models.choices import StaffState  # noqa: PLC0415

    user.username = f"deleted-{user.pk}"
    user.email = f"deleted-{user.pk}@deleted.invalid"
    user.name = ""
    user.date_of_birth = None
    user.accepted_tos = False
    user.is_active = False
    user.deactivation_reason = ""
    user.username_changed_at = None
    user.email_changed_at = None
    user.is_superuser = False
    user.__dict__["staff_state"] = StaffState.INACTIVE
    # The purge deletes EmailAddress rows below; do not let the User post_save
    # sync recreate one for the tombstone address.
    user.__dict__["_skip_email_sync"] = True
    user.save(
        update_fields=[
            "username",
            "email",
            "name",
            "date_of_birth",
            "accepted_tos",
            "is_active",
            "deactivation_reason",
            "username_changed_at",
            "email_changed_at",
            "is_superuser",
            "staff_state",
        ],
    )

    # allauth stores verified addresses separately; clear them too.
    user.emailaddress_set.all().delete()

    profile = getattr(user, "user_profile", None)
    if profile is not None:
        profile.access_needs = ""
        profile.access_needs_templates = []
        profile.bio = ""
        profile.profile_picture_url = ""
        profile.profile_picture_getpronto_id = ""
        profile.save(
            update_fields=[
                "access_needs",
                "access_needs_templates",
                "bio",
                "profile_picture_url",
                "profile_picture_getpronto_id",
                "updated_at",
            ],
        )

    peer_profile = getattr(user, "peer_profile", None)
    if peer_profile is not None:
        peer_profile.bio = ""
        peer_profile.default_terms = ""
        peer_profile.default_terms_updated_at = None
        peer_profile.terms_templates = []
        peer_profile.provider_agreement_accepted_at = None
        peer_profile.provider_agreement_version = ""
        peer_profile.is_approved = False
        peer_profile.approved_by = None
        peer_profile.approved_at = None
        peer_profile.is_verified = False
        peer_profile.verified_by = None
        peer_profile.verified_at = None
        peer_profile.save(
            update_fields=[
                "bio",
                "default_terms",
                "default_terms_updated_at",
                "terms_templates",
                "provider_agreement_accepted_at",
                "provider_agreement_version",
                "is_approved",
                "approved_by",
                "approved_at",
                "is_verified",
                "verified_by",
                "verified_at",
                "updated_at",
            ],
        )

    _scrub_payment_customer(user)


def _scrub_payment_customer(user) -> None:
    """Clear PII held on the local dj-stripe customer and payment profile."""
    payment_profile = getattr(user, "payment_profile", None)
    if payment_profile is None:
        return
    customer = getattr(payment_profile, "stripe_customer_id", None)
    if customer is not None:
        data = dict(customer.stripe_data or {})
        for key in ("name", "email", "phone", "address", "shipping", "description"):
            data.pop(key, None)
        customer.email = ""
        customer.stripe_data = data
        customer.save(update_fields=["email", "stripe_data"])
    payment_profile.kyc_completed = False
    payment_profile.save(update_fields=["kyc_completed", "updated_at"])


def purge_account(user, *, actor=None, request=None) -> None:
    """Anonymise *user* now, record a re-registration cooldown and audit it."""
    if user.username == f"deleted-{user.pk}":
        return  # already anonymised — never re-hash placeholder identities
    original_email = user.email
    original_username = user.username

    if user.is_active:
        deactivate_account(
            user,
            actor=actor,
            request=request,
            reason="Account deleted",
        )

    _cancel_stripe_subscription(user)
    _disconnect_stripe(user)

    with transaction.atomic():
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
    due = (
        AccountDeletionRequest.objects.filter(
            status=DeletionStatus.PENDING,
            scheduled_for__lte=now,
        )
        .select_related("user")
        .order_by("scheduled_for", "pk")
    )
    purged = 0
    for deletion in due:
        try:
            if deletion.user.is_active:
                # Never purge a reactivated account; drop the stale request.
                deletion.status = DeletionStatus.CANCELLED
                deletion.save(update_fields=["status", "updated_at"])
                continue
            purge_account(deletion.user)
        except Exception:
            logger.exception(
                "Failed to purge account deletion %s for user %s",
                deletion.pk,
                deletion.user_id,
            )
            continue
        purged += 1
    return purged
