"""Request-based audience predicates.

Each callable accepts an ``HttpRequest`` and returns ``bool``. Object-level
rules resolve their target from the URL kwargs (``request.daisie_path_params``)
or, as a fallback, the ``?user=`` query parameter. Staff and superusers
short-circuit to ``True`` where a moderator should see everything.

These predicates are plain Python; registering them in
``WAGTAIL_DAISIE_AUDIENCE_RULES`` happens in the daisIE track.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neuromancers_network.peers.services import is_eligible_peer

if TYPE_CHECKING:
    from django.http import HttpRequest

    from neuromancers_network.meetings.models import Meeting
    from neuromancers_network.users.models import User as UserType


def _request_user(request: HttpRequest) -> UserType | None:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


def _is_moderator(user: UserType | None) -> bool:
    return user is not None and bool(user.is_staff or user.is_superuser)


def _path_params(request: HttpRequest) -> dict:
    if request is None:
        return {}
    params = getattr(request, "daisie_path_params", None)
    if params:
        return dict(params)
    resolver_match = getattr(request, "resolver_match", None)
    kwargs = getattr(resolver_match, "kwargs", None)
    if kwargs:
        return dict(kwargs)
    return {}


def _target_user(request: HttpRequest) -> UserType | None:
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    user_model = get_user_model()
    params = _path_params(request)
    lookup: dict[str, object] = {}
    if "user_pk" in params:
        lookup["pk"] = params["user_pk"]
    elif "username" in params:
        lookup["username"] = params["username"]
    elif "user" in params:
        lookup["pk"] = params["user"]
    else:
        requested = getattr(request, "GET", {}).get("user")
        if not requested:
            return None
        if str(requested).isdigit():
            lookup["pk"] = requested
        else:
            lookup["username"] = requested
    return user_model.objects.filter(**lookup).first()


def _meeting(request: HttpRequest) -> Meeting | None:
    from neuromancers_network.meetings.models import Meeting  # noqa: PLC0415

    params = _path_params(request)
    pk = params.get("meeting_pk")
    if not pk:
        return None
    return Meeting.objects.filter(pk=pk).first()


def is_authenticated(request: HttpRequest) -> bool:
    return _request_user(request) is not None


def needs_tos_acceptance(request: HttpRequest) -> bool:
    """Signed-in members who have not yet accepted the Terms and Conditions."""
    user = _request_user(request)
    return user is not None and not user.accepted_tos


def is_deactivated(request: HttpRequest) -> bool:
    """Signed-in members whose account is deactivated."""
    user = _request_user(request)
    return user is not None and bool(getattr(user, "is_deactivated", False))


def is_moderator(request: HttpRequest) -> bool:
    return _is_moderator(_request_user(request))


def is_peer(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    return _is_moderator(user) or is_eligible_peer(user)


def is_verified_peer(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    return _is_moderator(user) or bool(getattr(user, "is_verified_peer", False))


def is_peer_owner(request: HttpRequest) -> bool:
    """An eligible care provider (or moderator) viewing their own profile."""
    return is_peer(request) and is_own_profile(request)


def is_meeting_host(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    if _is_moderator(user):
        return True
    meeting = _meeting(request)
    return meeting is not None and meeting.peer_id == user.pk


def is_meeting_seeker(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    if _is_moderator(user):
        return True
    meeting = _meeting(request)
    if meeting is None:
        return False
    return meeting.requests.filter(support_seeker=user).exists()


def is_meeting_participant(request: HttpRequest) -> bool:
    return is_meeting_host(request) or is_meeting_seeker(request)


def _join_target(request: HttpRequest):
    from neuromancers_network.meetings.join import resolve_join_target  # noqa: PLC0415

    user = _request_user(request)
    if user is None:
        return None
    params = _path_params(request)
    return resolve_join_target(
        user,
        meeting_pk=params.get("meeting_pk"),
        request_pk=params.get("meeting_request_pk") or params.get("request_pk"),
    )


def is_joining_upcoming_meeting_as_host(request: HttpRequest) -> bool:
    from neuromancers_network.meetings.join import target_is_open  # noqa: PLC0415

    target = _join_target(request)
    return bool(target and target.is_host and target_is_open(target))


def is_joining_upcoming_meeting_as_guest(request: HttpRequest) -> bool:
    from neuromancers_network.meetings.join import target_is_open  # noqa: PLC0415

    target = _join_target(request)
    return bool(target and target.is_guest and target_is_open(target))


def is_own_profile(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    target = _target_user(request)
    return target is not None and target.pk == user.pk


def is_own_profile_or_moderator(request: HttpRequest) -> bool:
    return is_moderator(request) or is_own_profile(request)


def is_bookmark_owner(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    if _is_moderator(user):
        return True
    params = _path_params(request)
    owner_pk = params.get("user_pk") or params.get("bookmark_user_pk")
    if owner_pk is None:
        return is_own_profile(request)
    return str(owner_pk) == str(user.pk)


def has_form_submission(request: HttpRequest) -> bool:
    """Signed-in member has an existing peer application submission."""
    user = _request_user(request)
    if user is None:
        return False
    from neuromancers_network.peers.models import PeerApplication  # noqa: PLC0415

    return PeerApplication.objects.filter(user=user).exists()


def has_no_form_submission(request: HttpRequest) -> bool:
    """Signed-in member has no existing peer application submission."""
    user = _request_user(request)
    return user is not None and not has_form_submission(request)


def _profile(user):
    return getattr(user, "peer_profile", None)


def _payment(user):
    return getattr(user, "payment_profile", None)


def _peer_subscription(user):
    payment = _payment(user)
    return getattr(payment, "peer_subscription", None) if payment else None


def _subscription(user):
    peer_subscription = _peer_subscription(user)
    return (
        getattr(peer_subscription, "subscription", None) if peer_subscription else None
    )


def _application(user):
    return getattr(user, "peer_application", None)


def is_deleting_account(request: HttpRequest) -> bool:
    """Signed-in member with a pending account deletion request."""
    user = _request_user(request)
    if user is None:
        return False
    from neuromancers_network.moderation.models import AccountDeletionRequest  # noqa: PLC0415
    from neuromancers_network.moderation.models import DeletionStatus  # noqa: PLC0415

    return AccountDeletionRequest.objects.filter(
        user=user,
        status=DeletionStatus.PENDING,
    ).exists()


def can_delete_account(request: HttpRequest) -> bool:
    user = _request_user(request)
    return bool(
        user
        and not getattr(user, "is_deactivated", False)
        and not is_deleting_account(request),
    )


def can_cancel_account_deletion(request: HttpRequest) -> bool:
    return is_deleting_account(request)


def can_deactivate_account(request: HttpRequest) -> bool:
    return can_delete_account(request)


def can_reactivate_account(request: HttpRequest) -> bool:
    user = _request_user(request)
    return bool(user and getattr(user, "is_deactivated", False))


def can_accept_tos(request: HttpRequest) -> bool:
    return needs_tos_acceptance(request)


def has_peer_profile(request: HttpRequest) -> bool:
    user = _request_user(request)
    return user is not None and _profile(user) is not None


def has_peer_application(request: HttpRequest) -> bool:
    user = _request_user(request)
    return user is not None and _application(user) is not None


def peer_application_pending(request: HttpRequest) -> bool:
    user = _request_user(request)
    application = _application(user) if user else None
    if application is None:
        return False
    from neuromancers_network.peers.models import PeerApplicationStatus  # noqa: PLC0415

    return application.status == PeerApplicationStatus.PENDING


def peer_application_rejected(request: HttpRequest) -> bool:
    user = _request_user(request)
    application = _application(user) if user else None
    if application is None:
        return False
    from neuromancers_network.peers.models import PeerApplicationStatus  # noqa: PLC0415

    return application.status == PeerApplicationStatus.REJECTED


def is_approved_provider(request: HttpRequest) -> bool:
    user = _request_user(request)
    profile = _profile(user) if user else None
    return bool(profile and profile.is_approved)


def is_verified_provider(request: HttpRequest) -> bool:
    user = _request_user(request)
    profile = _profile(user) if user else None
    return bool(profile and profile.is_verified)


def provider_settings(request: HttpRequest) -> bool:
    user = _request_user(request)
    return bool(
        user and (_profile(user) is not None or _application(user) is not None),
    )


def can_apply_as_peer(request: HttpRequest) -> bool:
    user = _request_user(request)
    return bool(
        user and _profile(user) is None and _application(user) is None,
    )


def has_accepted_provider_agreement(request: HttpRequest) -> bool:
    user = _request_user(request)
    profile = _profile(user) if user else None
    return bool(profile and profile.has_accepted_provider_agreement)


def can_accept_provider_agreement(request: HttpRequest) -> bool:
    user = _request_user(request)
    profile = _profile(user) if user else None
    return bool(
        profile and profile.is_approved and not profile.has_accepted_provider_agreement,
    )


def has_connected_stripe(request: HttpRequest) -> bool:
    payment = _payment(_request_user(request))
    return bool(payment and payment.stripe_connect_account_id_id)


def has_completed_kyc(request: HttpRequest) -> bool:
    payment = _payment(_request_user(request))
    return bool(payment and payment.kyc_completed)


def has_active_plan(request: HttpRequest) -> bool:
    payment = _payment(_request_user(request))
    return bool(payment and payment.has_active_subscription)


def has_paused_plan(request: HttpRequest) -> bool:
    peer_subscription = _peer_subscription(_request_user(request))
    return bool(peer_subscription and peer_subscription.paused_at is not None)


def has_past_due_plan(request: HttpRequest) -> bool:
    subscription = _subscription(_request_user(request))
    if subscription is None:
        return False
    return subscription.status in {"past_due", "unpaid"}


def has_cancelled_plan(request: HttpRequest) -> bool:
    subscription = _subscription(_request_user(request))
    if subscription is None:
        return False
    return bool(
        getattr(subscription, "cancel_at_period_end", False)
        or subscription.status in {"canceled", "incomplete_expired"},
    )


def has_plan(request: HttpRequest) -> bool:
    return _peer_subscription(_request_user(request)) is not None


def can_start_plan(request: HttpRequest) -> bool:
    return bool(
        is_approved_provider(request)
        and has_accepted_provider_agreement(request)
        and not has_plan(request),
    )


def can_pause_plan(request: HttpRequest) -> bool:
    return has_active_plan(request) and not has_cancelled_plan(request)


def can_resume_plan(request: HttpRequest) -> bool:
    return has_paused_plan(request)


def can_cancel_plan(request: HttpRequest) -> bool:
    return bool(
        has_plan(request)
        and not has_cancelled_plan(request)
        and (
            has_active_plan(request)
            or has_paused_plan(request)
            or has_past_due_plan(request)
        ),
    )


def can_connect_stripe(request: HttpRequest) -> bool:
    return bool(
        is_approved_provider(request)
        and has_accepted_provider_agreement(request)
        and not has_connected_stripe(request),
    )


def can_open_stripe_dashboard(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    return bool(
        has_connected_stripe(request)
        and has_completed_kyc(request)
        and is_eligible_peer(user),
    )


def can_disconnect_stripe(request: HttpRequest) -> bool:
    return has_connected_stripe(request)


def has_active_calendar_feed(request: HttpRequest) -> bool:
    user = _request_user(request)
    token = getattr(user, "calendar_feed_token", None) if user else None
    return bool(token and token.is_active)


def can_rotate_calendar_feed(request: HttpRequest) -> bool:
    return is_authenticated(request)


def can_revoke_calendar_feed(request: HttpRequest) -> bool:
    return has_active_calendar_feed(request)


def has_active_data_export(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    from neuromancers_network.moderation.models import DataExportRequest  # noqa: PLC0415
    from neuromancers_network.moderation.models import ExportStatus  # noqa: PLC0415

    return DataExportRequest.objects.filter(
        user=user,
        status__in=[ExportStatus.PENDING, ExportStatus.PROCESSING],
    ).exists()


def has_recent_data_export(request: HttpRequest) -> bool:
    user = _request_user(request)
    if user is None:
        return False
    from datetime import timedelta  # noqa: PLC0415

    from django.utils import timezone  # noqa: PLC0415

    from neuromancers_network.moderation.models import DataExportRequest  # noqa: PLC0415
    from neuromancers_network.moderation.models import ExportStatus  # noqa: PLC0415

    cutoff = timezone.now() - timedelta(hours=24)
    return DataExportRequest.objects.filter(
        user=user,
        status=ExportStatus.READY,
        completed_at__gte=cutoff,
    ).exists()


def can_request_data_export(request: HttpRequest) -> bool:
    return bool(
        is_authenticated(request)
        and not has_active_data_export(request)
        and not has_recent_data_export(request),
    )


# --- Queryset factories (request-less audiences: campaigns, resets) ----------


def authenticated_users():
    """Active users (the ``authenticated`` audience queryset)."""
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    return get_user_model().objects.filter(is_active=True)


def peer_users():
    """Currently eligible care providers."""
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    from neuromancers_network.peers.services import eligible_peer_q  # noqa: PLC0415

    return get_user_model().objects.filter(eligible_peer_q())


def verified_peer_users():
    """Currently eligible, verified care providers."""
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    from neuromancers_network.peers.services import eligible_peer_q  # noqa: PLC0415

    return get_user_model().objects.filter(
        eligible_peer_q(),
        peer_profile__is_verified=True,
    )


def moderator_users():
    """Active staff and superusers."""
    from django.contrib.auth import get_user_model  # noqa: PLC0415
    from django.db.models import Q  # noqa: PLC0415

    from neuromancers_network.users.models import StaffState  # noqa: PLC0415

    return get_user_model().objects.filter(
        Q(is_superuser=True) | Q(staff_state=StaffState.ACTIVE),
    )


def needs_tos_acceptance_users():
    """Active members who have not accepted the Terms and Conditions."""
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    return get_user_model().objects.filter(is_active=True, accepted_tos=False)


def deactivated_users():
    """Members whose account is deactivated."""
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    return get_user_model().objects.filter(deactivated_at__isnull=False)
