from unittest.mock import patch

import pytest

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import RefundStatus
from neuromancers_network.meetings.models import Review
from neuromancers_network.notifications.models import NotificationEventLog
from neuromancers_network.peers.models import PeerApplication
from neuromancers_network.users.tests.factories import PeerProfileFactory
from neuromancers_network.users.tests.factories import PeerSubscriptionFactory
from neuromancers_network.users.tests.factories import UserFactory

from .factories import make_meeting
from .factories import make_request

pytestmark = pytest.mark.django_db


def events_for(event_type, event_ref):
    return NotificationEventLog.objects.filter(
        event_type=event_type,
        event_ref=event_ref,
    )


class TestBookingEvents:
    def test_create_emits_booking_requested(self):
        meeting = make_meeting(UserFactory())
        request = make_request(meeting)

        assert events_for(
            "booking_requested",
            f"meetingrequest.{request.pk}.requested",
        ).exists()

    def test_reject_emits_booking_rejected(self):
        meeting = make_meeting(UserFactory())
        request = make_request(meeting)
        NotificationEventLog.objects.all().delete()

        request.reject()
        request.save()

        assert events_for(
            "booking_rejected",
            f"meetingrequest.{request.pk}.reject",
        ).exists()

    def test_approve_then_cancel_emit_transition_events(self):
        meeting = make_meeting(UserFactory())
        request = make_request(meeting)
        NotificationEventLog.objects.all().delete()

        request.approve()
        request.save()
        request.cancel()
        request.save()

        assert events_for(
            "booking_approved",
            f"meetingrequest.{request.pk}.approve",
        ).exists()
        assert events_for(
            "booking_cancelled",
            f"meetingrequest.{request.pk}.cancel",
        ).exists()

    def test_mark_paid_emits_booking_paid(self):
        meeting = make_meeting(UserFactory())
        request = make_request(meeting)
        request.approve()
        request.save()
        NotificationEventLog.objects.all().delete()

        request.mark_paid()
        request.save()

        assert events_for(
            "booking_paid",
            f"meetingrequest.{request.pk}.mark_paid",
        ).exists()


class TestRefundEvents:
    def test_immediate_refund_emits_requested_and_refunded(self):
        StripeSettings.objects.create(secret_key="sk_test_123")  # noqa: S106
        meeting = make_meeting(
            UserFactory(),
            approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
            refund_requires_approval=False,
        )
        request = make_request(meeting)
        request.__dict__["status"] = MeetingRequestStatus.PAID
        request.stripe_payment_intent_id = "pi_test_123"
        request.save()
        NotificationEventLog.objects.all().delete()

        with (
            patch(
                "neuromancers_network.meetings.models.refund.stripe.Refund.create",
            ) as create_refund,
            patch(
                "neuromancers_network.meetings.models.refund.StripeRefund.sync_from_stripe_data",
            ),
        ):
            create_refund.return_value = type("Refund", (), {"id": "re_123"})()
            refund_request = request.request_refund("Not happy")

        refund_request.refresh_from_db()
        assert refund_request.status == RefundStatus.REFUNDED
        assert events_for(
            "refund_requested",
            f"refundrequest.{refund_request.pk}.requested",
        ).exists()
        assert events_for(
            "refund_refunded",
            f"refundrequest.{refund_request.pk}.mark_refunded",
        ).exists()


class TestReviewEvents:
    def test_review_create_emits_review_created(self):
        peer = UserFactory()
        seeker = UserFactory()
        meeting = make_meeting(peer)
        request = make_request(meeting, seeker)
        NotificationEventLog.objects.all().delete()

        review = Review.objects.create(
            meeting_request=request,
            reviewer=seeker,
            peer=peer,
            rating=5,
        )

        assert events_for(
            "review_created",
            f"review.{review.pk}.created",
        ).exists()


class TestPeerApprovalEvents:
    def test_peer_profile_approval_emits_peer_approved(self):
        profile = PeerProfileFactory(is_approved=False)
        moderator = UserFactory()
        NotificationEventLog.objects.all().delete()

        profile.is_approved = True
        profile.approved_by = moderator
        profile.save()

        assert events_for(
            "peer_approved",
            f"peerprofile.{profile.pk}.approved",
        ).exists()

    def test_peer_application_approval_emits_event(self):
        application = PeerApplication.objects.create(
            user=UserFactory(),
            reason="I want to help",
        )
        moderator = UserFactory()
        NotificationEventLog.objects.all().delete()

        application.status = "approved"
        application.reviewed_by = moderator
        application.save()

        assert events_for(
            "peer_application_approved",
            f"peerapplication.{application.pk}.approved",
        ).exists()


class TestSubscriptionEvents:
    def test_peer_subscription_create_emits_subscription_created(self):
        peer_subscription = PeerSubscriptionFactory()
        assert events_for(
            "subscription_created",
            f"peersubscription.{peer_subscription.pk}.created",
        ).exists()

    def test_subscription_cancel_emits_subscription_cancelled(self):
        peer_subscription = PeerSubscriptionFactory()
        NotificationEventLog.objects.all().delete()

        subscription = peer_subscription.subscription
        subscription.stripe_data["status"] = "canceled"
        subscription.save()

        assert events_for(
            "subscription_cancelled",
            f"subscription.{subscription.pk}.cancelled",
        ).exists()


class TestMeetingCancelledEvents:
    def test_archive_from_published_emits_meeting_cancelled(self):
        peer = UserFactory()
        seeker = UserFactory()
        meeting = make_meeting(peer)
        make_request(meeting, seeker)
        NotificationEventLog.objects.all().delete()

        meeting.archive()
        meeting.save()

        assert events_for(
            "meeting_cancelled",
            f"meeting.{meeting.pk}.cancelled",
        ).exists()
