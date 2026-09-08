"""Database-event receivers that push business events onto the event bus.

Receivers are defensive: they never raise into the caller. Emission is a
side-effect that must not break the transaction that caused the event.
"""

import logging

from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django_fsm.signals import post_transition
from djstripe.models import Subscription as StripeSubscription

from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import RefundRequest
from neuromancers_network.meetings.models import Review
from neuromancers_network.peers.models import PeerApplication
from neuromancers_network.peers.models import PeerProfile
from neuromancers_network.peers.models import PeerSubscription

from .events import emit
from .payloads import booking_payload
from .payloads import refund_payload
from .payloads import review_payload
from .payloads import user_id

logger = logging.getLogger(__name__)

# For these models a state change is detected by comparing the value already
# stored in the database (read in pre_save) with the value being written.
# ``StripeSubscription`` keeps its status inside the ``stripe_data`` JSON column
# rather than as a real field.
_EVENT_SNAPSHOT_SPEC = {
    PeerProfile: ("is_approved",),
    PeerApplication: ("status",),
    StripeSubscription: ("stripe_data",),
}

# Stashed pre-save values, keyed by (model class id, object pk). A module-level
# store avoids attaching ad-hoc private attributes to Django model instances.
_pre_state_store: dict[tuple[int, object], dict] = {}


def _read_previous(sender, pk, spec_fields):
    """Return the pre-save values read from the database for *instance*."""
    row = sender.objects.filter(pk=pk).values(*spec_fields).first()
    if row is None:
        return None
    if "stripe_data" in spec_fields:
        data = row["stripe_data"] or {}
        return {"status": data.get("status")}
    return row


def _stash_pre_state(sender, instance, **kwargs):
    """Remember the database values before an update is written."""
    if instance.pk is None:
        return
    spec_fields = _EVENT_SNAPSHOT_SPEC.get(sender)
    if spec_fields is None:
        return
    previous = _read_previous(sender, instance.pk, spec_fields)
    if previous is not None:
        _pre_state_store[(id(sender), instance.pk)] = previous


def _drop_pre_state(instance) -> dict:
    return _pre_state_store.pop((id(instance.__class__), instance.pk), {})


# --- MeetingRequest: booking events ----------------------------------------


def emit_booking_requested(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        emit(
            "booking_requested",
            payload=booking_payload(
                instance,
                actor=instance.support_seeker,
                recipients=[instance.meeting.peer],
            ),
            event_ref=f"meetingrequest.{instance.pk}.requested",
        )
    except Exception:
        logger.exception("Failed to emit booking_requested event")


def emit_booking_transition(sender, instance, name, source, target, **kwargs):
    seeker = instance.support_seeker
    peer = instance.meeting.peer
    mapping = {
        "approve": ("booking_approved", peer, [seeker]),
        "reject": ("booking_rejected", peer, [seeker]),
        "mark_paid": ("booking_paid", seeker, [peer]),
        "complete": ("booking_completed", None, [seeker, peer]),
        "cancel": ("booking_cancelled", None, [seeker, peer]),
    }
    if name not in mapping:
        return
    event_type, actor, recipients = mapping[name]
    try:
        emit(
            event_type,
            payload=booking_payload(instance, actor=actor, recipients=recipients),
            event_ref=f"meetingrequest.{instance.pk}.{name}",
        )
    except Exception:
        logger.exception("Failed to emit %s event", event_type)


# --- RefundRequest: refund events ------------------------------------------


def emit_refund_requested(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        request = instance.meeting_request
        emit(
            "refund_requested",
            payload=refund_payload(
                instance,
                actor=request.support_seeker,
                recipients=[request.meeting.peer],
            ),
            event_ref=f"refundrequest.{instance.pk}.requested",
        )
    except Exception:
        logger.exception("Failed to emit refund_requested event")


def emit_refund_transition(sender, instance, name, source, target, **kwargs):
    request = instance.meeting_request
    mapping = {
        "approve": (
            "refund_approved",
            request.meeting.peer,
            [request.support_seeker],
        ),
        "reject": (
            "refund_rejected",
            request.meeting.peer,
            [request.support_seeker],
        ),
        "mark_refunded": ("refund_refunded", None, [request.support_seeker]),
    }
    if name not in mapping:
        return
    event_type, actor, recipients = mapping[name]
    try:
        emit(
            event_type,
            payload=refund_payload(instance, actor=actor, recipients=recipients),
            event_ref=f"refundrequest.{instance.pk}.{name}",
        )
    except Exception:
        logger.exception("Failed to emit %s event", event_type)


# --- Review -----------------------------------------------------------------


def emit_review_created(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        emit(
            "review_created",
            payload=review_payload(
                instance,
                actor=instance.reviewer,
                recipients=[instance.peer],
            ),
            event_ref=f"review.{instance.pk}.created",
        )
    except Exception:
        logger.exception("Failed to emit review_created event")


# --- Peer approval ----------------------------------------------------------


def emit_peer_profile_changed(sender, instance, created, **kwargs):
    previous = _drop_pre_state(instance)
    was_approved = previous.get("is_approved", False)
    if not created and was_approved:
        return
    if not instance.is_approved:
        return
    try:
        emit(
            "peer_approved",
            payload={
                "actor_user_id": user_id(instance.approved_by),
                "recipient_user_ids": [user_id(instance.user)],
                "object_type": "peerprofile",
                "object_id": instance.pk,
                "meta": {
                    "peer_profile_id": instance.pk,
                    "peer_user_id": user_id(instance.user),
                    "approved_by_user_id": user_id(instance.approved_by),
                },
            },
            event_ref=f"peerprofile.{instance.pk}.approved",
        )
    except Exception:
        logger.exception("Failed to emit peer_approved event")


def emit_peer_application_changed(sender, instance, created, **kwargs):
    previous = _drop_pre_state(instance)
    if instance.status not in ("approved", "rejected"):
        return
    if not created and previous.get("status") == instance.status:
        return
    event_type = (
        "peer_application_approved"
        if instance.status == "approved"
        else "peer_application_rejected"
    )
    try:
        emit(
            event_type,
            payload={
                "actor_user_id": user_id(instance.reviewed_by),
                "recipient_user_ids": [user_id(instance.user)],
                "object_type": "peerapplication",
                "object_id": instance.pk,
                "meta": {
                    "peer_application_id": instance.pk,
                    "peer_user_id": user_id(instance.user),
                    "status": instance.status,
                    "reviewed_by_user_id": user_id(instance.reviewed_by),
                },
            },
            event_ref=f"peerapplication.{instance.pk}.{instance.status}",
        )
    except Exception:
        logger.exception("Failed to emit %s event", event_type)


# --- Subscriptions ----------------------------------------------------------


def emit_subscription_created(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        user = instance.payment_profile.user
        emit(
            "subscription_created",
            payload={
                "actor_user_id": user_id(user),
                "recipient_user_ids": [user_id(user)],
                "object_type": "peersubscription",
                "object_id": instance.pk,
                "meta": {
                    "peer_subscription_id": instance.pk,
                    "subscription_id": instance.subscription_id,
                    "peer_user_id": user_id(user),
                },
            },
            event_ref=f"peersubscription.{instance.pk}.created",
        )
    except Exception:
        logger.exception("Failed to emit subscription_created event")


def emit_subscription_cancelled(sender, instance, created, **kwargs):
    if created:
        return
    previous = _drop_pre_state(instance)
    if previous.get("status") == "canceled" or instance.status != "canceled":
        return
    try:
        peer_subscription = instance.peer_subscription
    except PeerSubscription.DoesNotExist:
        peer_subscription = None
    user = (
        peer_subscription.payment_profile.user
        if peer_subscription is not None
        else None
    )
    try:
        emit(
            "subscription_cancelled",
            payload={
                "actor_user_id": user_id(user),
                "recipient_user_ids": [user_id(user)] if user else [],
                "object_type": "subscription",
                "object_id": instance.pk,
                "meta": {
                    "subscription_id": instance.pk,
                    "status": instance.status,
                    "peer_user_id": user_id(user),
                },
            },
            event_ref=f"subscription.{instance.pk}.cancelled",
        )
    except Exception:
        logger.exception("Failed to emit subscription_cancelled event")


# --- Meeting: cancelled (archive from published) ----------------------------


def emit_meeting_cancelled(sender, instance, name, source, target, **kwargs):
    if name != "archive":
        return
    try:
        requests = list(
            instance.requests.select_related("support_seeker").all(),
        )
        recipients = [instance.peer]
        recipients += [req.support_seeker for req in requests]
        emit(
            "meeting_cancelled",
            payload={
                "actor_user_id": user_id(instance.peer),
                "recipient_user_ids": [
                    user_id(user) for user in recipients if user is not None
                ],
                "object_type": "meeting",
                "object_id": instance.pk,
                "meta": {
                    "meeting_id": instance.pk,
                    "meeting_title": instance.title,
                    "peer_user_id": user_id(instance.peer),
                    "scheduled_at": (
                        instance.scheduled_at.isoformat()
                        if instance.scheduled_at
                        else None
                    ),
                    "booked_seeker_user_ids": [
                        user_id(req.support_seeker) for req in requests
                    ],
                },
            },
            event_ref=f"meeting.{instance.pk}.cancelled",
        )
    except Exception:
        logger.exception("Failed to emit meeting_cancelled event")


# --- Wiring -----------------------------------------------------------------

post_save.connect(emit_booking_requested, sender=MeetingRequest)
post_transition.connect(emit_booking_transition, sender=MeetingRequest)
post_save.connect(emit_refund_requested, sender=RefundRequest)
post_transition.connect(emit_refund_transition, sender=RefundRequest)
post_save.connect(emit_review_created, sender=Review)
post_transition.connect(emit_meeting_cancelled, sender=Meeting)

# Peer profile / application (plain-field state changes)
pre_save.connect(_stash_pre_state, sender=PeerProfile)
post_save.connect(emit_peer_profile_changed, sender=PeerProfile)
pre_save.connect(_stash_pre_state, sender=PeerApplication)
post_save.connect(emit_peer_application_changed, sender=PeerApplication)

# PeerSubscription + djstripe Subscription
post_save.connect(emit_subscription_created, sender=PeerSubscription)
pre_save.connect(_stash_pre_state, sender=StripeSubscription)
post_save.connect(emit_subscription_cancelled, sender=StripeSubscription)
