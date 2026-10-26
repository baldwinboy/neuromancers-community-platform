import logging
from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.utils import timezone
from djstripe.enums import SubscriptionStatus

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingRequest
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers import signals
from neuromancers_network.peers.actions import availability_create
from neuromancers_network.peers.actions import availability_delete
from neuromancers_network.peers.actions import peer_accept_provider_agreement
from neuromancers_network.peers.actions import peer_connect_stripe
from neuromancers_network.peers.actions import peer_stripe_disconnect
from neuromancers_network.peers.actions import peer_subscribe
from neuromancers_network.peers.models import CalendarEvent
from neuromancers_network.peers.models import PeerApplication
from neuromancers_network.peers.models import PeerApplicationStatus
from neuromancers_network.peers.models import PeerAvailability
from neuromancers_network.peers.models.profile import PROVIDER_AGREEMENT_VERSION
from neuromancers_network.peers.models.settings import PeerRequirementsSettings
from neuromancers_network.peers.selectors import peer_calendar_events
from neuromancers_network.peers.services import MAX_RECURRENCE_OCCURRENCES
from neuromancers_network.peers.services import available_slots
from neuromancers_network.peers.services import eligibility_failures
from neuromancers_network.peers.services import eligible_peer_q
from neuromancers_network.peers.services import enforce_subscription_lapse
from neuromancers_network.peers.services import is_eligible_peer
from neuromancers_network.peers.services import window_occurrences
from neuromancers_network.peers.tests.factories import make_availability
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

User = get_user_model()

EXPECTED_DAILY_SLOTS = 3
EXPECTED_START_HOUR = 9
EXPECTED_END_HOUR = 11


class TestEligibility:
    def test_unknown_user_is_not_eligible(self):
        assert is_eligible_peer(None) is False

    def test_user_without_peer_profile(self, user):
        assert is_eligible_peer(user) is False
        assert "not_approved" in eligibility_failures(user)

    def test_full_peer_is_eligible(self):
        assert is_eligible_peer(make_peer()) is True

    def test_eligible_peer_q_matches_only_eligible_users(self):
        eligible = make_peer()
        make_peer(is_approved=False)

        assert list(User.objects.filter(eligible_peer_q())) == [eligible]

    def test_unapproved_peer_is_not_eligible(self):
        assert is_eligible_peer(make_peer(is_approved=False)) is False

    def test_missing_subscription(self):
        user = make_peer(subscription_status=None)
        assert "no_active_subscription" in eligibility_failures(user)
        assert is_eligible_peer(user) is False

    def test_incomplete_kyc(self):
        user = make_peer(kyc_completed=False)
        assert "kyc_incomplete" in eligibility_failures(user)

    def test_verification_requirement_toggle(self):
        config = PeerRequirementsSettings.load()
        config.require_verification_to_publish = True
        config.save()

        user = make_peer(is_verified=False)
        assert "not_verified" in eligibility_failures(user)

    def test_verification_requirement_met(self):
        config = PeerRequirementsSettings.load()
        config.require_verification_to_publish = True
        config.save()

        user = make_peer(is_verified=True)
        assert is_eligible_peer(user) is True


def make_group_meeting(peer, *, status=MeetingStatus.PUBLISHED):
    meeting = Meeting(
        peer=peer,
        title="Group",
        description="Test",
        meeting_type=MeetingType.GROUP,
        pricing_type=PricingType.FIXED,
        price=Decimal("5.00"),
        approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
        currency="GBP",
        scheduled_at=timezone.now() + timedelta(days=3),
        duration_minutes=60,
        status=status,
    )
    meeting.save(validate=False)
    return meeting


class TestSubscriptionLapse:
    def test_unpublishes_one_to_one_meeting(self):
        peer = make_peer()
        meeting = create_meeting(peer=peer)

        enforce_subscription_lapse(peer.payment_profile)

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.DRAFT

    def test_unpublishes_group_without_paid_participants(self):
        peer = make_peer()
        meeting = make_group_meeting(peer)

        enforce_subscription_lapse(peer.payment_profile)

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.DRAFT

    def test_keeps_group_with_paid_participant_published(self):
        peer = make_peer()
        meeting = make_group_meeting(peer)
        MeetingRequest.objects.create(
            meeting=meeting,
            support_seeker=UserFactory(),
            status=MeetingRequestStatus.PAID,
        )

        enforce_subscription_lapse(peer.payment_profile)

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.PUBLISHED

    def test_ignores_already_unpublished_meetings(self):
        peer = make_peer()
        meeting = create_meeting(peer=peer, status=MeetingStatus.DRAFT)

        enforce_subscription_lapse(peer.payment_profile)

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.DRAFT


class TestSubscriptionLapseSignal:
    def test_lapse_runs_when_subscription_is_removed(self, monkeypatch):
        peer = make_peer()
        meeting = create_meeting(peer=peer)
        event = SimpleNamespace(
            type="customer.subscription.deleted",
            data={
                "object": {
                    "id": "sub_lapsed",
                    "customer": peer.payment_profile.stripe_customer_id_id,
                    "status": "canceled",
                },
            },
            default_api_key="sk_test",
        )
        monkeypatch.setattr(
            signals.StripeSubscription,
            "sync_from_stripe_data",
            lambda data, api_key=None: None,
        )

        signals.sync_peer_subscription(sender=None, event=event)

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.DRAFT


def _approved_request(peer, *, start, minutes):
    meeting = create_meeting(peer=peer)
    request = MeetingRequest(
        meeting=meeting,
        support_seeker=UserFactory(),
        requested_start_time=start,
        requested_duration_minutes=minutes,
    )
    request.start()  # PAY_AFTER_JOIN -> APPROVED
    request.save()
    return request


class TestAvailableSlots:
    def test_no_windows_means_no_slots(self):
        assert available_slots(make_peer()) == []

    def test_one_off_window(self):
        peer = make_peer()
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)
        make_availability(peer, start=start, end=end)

        assert available_slots(peer) == [(start, end)]

    def test_recurring_daily_expands(self):
        peer = make_peer()
        base = (timezone.now() + timedelta(days=1)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        make_availability(
            peer,
            start=base,
            end=base + timedelta(hours=1),
            occurrence="daily",
            occurrence_starts_at=base,
            occurrence_ends_at=base + timedelta(days=2),
        )

        slots = available_slots(peer)
        assert len(slots) == EXPECTED_DAILY_SLOTS
        assert slots[0] == (base, base + timedelta(hours=1))

    def test_overnight_recurring_window(self):
        peer = make_peer()
        base = (timezone.now() + timedelta(days=1)).replace(
            hour=22,
            minute=0,
            second=0,
            microsecond=0,
        )
        make_availability(
            peer,
            start=base,
            end=base + timedelta(hours=4),
            occurrence="daily",
            occurrence_starts_at=base,
            occurrence_ends_at=base + timedelta(days=1),
        )

        start, end = available_slots(peer)[0]
        assert start == base
        assert end == base + timedelta(hours=4)

    def test_booked_time_is_removed(self):
        peer = make_peer()
        base = (timezone.now() + timedelta(days=2)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        make_availability(
            peer,
            start=base,
            end=base + timedelta(hours=3),
        )
        _approved_request(peer, start=base + timedelta(hours=1), minutes=60)

        assert available_slots(peer) == [
            (base, base + timedelta(hours=1)),
            (base + timedelta(hours=2), base + timedelta(hours=3)),
        ]

    def test_fully_booked_slot_is_removed(self):
        peer = make_peer()
        base = (timezone.now() + timedelta(days=2)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        make_availability(peer, start=base, end=base + timedelta(hours=1))
        _approved_request(peer, start=base, minutes=60)

        assert available_slots(peer) == []


class TestCalendarSync:
    def _window(self, peer):
        start = (timezone.now() + timedelta(days=2)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        return make_availability(peer, start=start, end=start + timedelta(hours=1))

    def test_window_creates_available_event(self):
        peer = make_peer()
        window = self._window(peer)

        assert (
            CalendarEvent.objects.filter(
                source_type="availability",
                source_id=window.pk,
                kind="available",
            ).count()
            == 1
        )

    def test_deleting_window_removes_event(self):
        peer = make_peer()
        window = self._window(peer)
        window.delete()

        assert not CalendarEvent.objects.filter(
            source_type="availability",
            source_id=window.pk,
        ).exists()


class TestPeerCalendarEvents:
    def _request(self, viewer, profile=None):
        request = RequestFactory().get("/")
        request.user = viewer
        if profile is not None:
            request.daisie_path_params = {"peer_pk": profile.pk}
        return request

    def _window(self, peer):
        start = (timezone.now() + timedelta(days=2)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        return make_availability(peer, start=start, end=start + timedelta(hours=1))

    def test_owner_sees_events(self):
        peer = make_peer()
        self._window(peer)

        events = peer_calendar_events(self._request(peer, peer.peer_profile))
        assert events.count() == 1

    def test_unpublished_calendar_hidden_from_others(self):
        peer = make_peer()
        self._window(peer)
        viewer = make_peer()

        events = peer_calendar_events(self._request(viewer, peer.peer_profile))
        assert events.count() == 0

    def test_published_calendar_shows_availability(self):
        peer = make_peer()
        profile, _created = UserProfile.objects.get_or_create(user=peer)
        profile.show_calendar = True
        profile.save()
        self._window(peer)
        viewer = make_peer()

        events = peer_calendar_events(self._request(viewer, peer.peer_profile))
        assert [event.display_title for event in events] == ["Available"]


def _post(user):
    request = RequestFactory().post("/", {})
    request.user = user
    return request


class TestAvailabilityActions:
    def test_create_window(self):
        peer = make_peer()

        availability_create(
            _post(peer),
            {
                "start": "2026-11-01T09:00",
                "end": "2026-11-01T11:00",
                "occurrence": "daily",
            },
        )

        window = PeerAvailability.objects.get(peer=peer)
        assert window.start.hour == EXPECTED_START_HOUR
        assert window.end.hour == EXPECTED_END_HOUR
        assert window.occurrence == "daily"

    def test_owner_can_delete(self):
        peer = make_peer()
        start = timezone.now() + timedelta(days=1)
        window = make_availability(peer, start=start, end=start + timedelta(hours=1))

        availability_delete(_post(peer), {"target": window.pk})

        assert not PeerAvailability.objects.filter(pk=window.pk).exists()

    def test_delete_requires_ownership(self):
        peer = make_peer()
        start = timezone.now() + timedelta(days=1)
        window = make_availability(peer, start=start, end=start + timedelta(hours=1))

        with pytest.raises(PermissionDenied):
            availability_delete(_post(make_peer()), {"target": window.pk})


class TestRecurrenceClamp:
    def test_expansion_stops_at_the_cap(self, caplog):
        now = timezone.now()
        horizon = now + timedelta(days=365 * 10)
        window = SimpleNamespace(
            pk=1,
            start=now,
            end=now + timedelta(hours=1),
            occurrence="daily",
            occurrence_starts_at=now,
            occurrence_ends_at=horizon,
        )

        with caplog.at_level(
            logging.WARNING,
            logger="neuromancers_network.peers.services",
        ):
            occurrences = list(window_occurrences(window, now, horizon))

        assert len(occurrences) == MAX_RECURRENCE_OCCURRENCES
        assert "Stopped expanding availability window" in caplog.text


class TestPeerProfileDefaultTerms:
    def test_stamp_is_persisted_with_update_fields(self):
        profile = make_peer().peer_profile

        profile.default_terms = "New terms"
        profile.save(update_fields=["default_terms"])

        profile.refresh_from_db()
        assert profile.default_terms_updated_at is not None


class TestPeerApplicationTransitions:
    def _application(self):
        return PeerApplication.objects.create(user=UserFactory(), reason="Help")

    def test_direct_status_rejection_is_honoured(self):
        application = self._application()
        application.approve()
        assert application.is_approved is True

        application.status = PeerApplicationStatus.REJECTED
        application.save()

        application.refresh_from_db()
        assert application.status == PeerApplicationStatus.REJECTED
        assert application.is_approved is False

    def test_rejecting_approved_application_is_refused(self):
        application = self._application()
        profile = application.approve()

        with pytest.raises(ValueError, match="approved application"):
            application.reject()

        application.refresh_from_db()
        profile.refresh_from_db()
        assert application.status == PeerApplicationStatus.APPROVED
        assert application.is_approved is True
        assert profile.is_approved is True

    def test_approve_from_rejected_is_allowed(self):
        application = self._application()
        application.reject()

        profile = application.approve()

        application.refresh_from_db()
        profile.refresh_from_db()
        assert application.status == PeerApplicationStatus.APPROVED
        assert application.is_approved is True
        assert profile.is_approved is True


class TestStripeDisconnectAction:
    def test_balance_blocks_disconnect_with_message(self):
        from django.contrib.messages import get_messages  # noqa: PLC0415
        from django.contrib.messages.middleware import MessageMiddleware  # noqa: PLC0415
        from django.contrib.sessions.middleware import SessionMiddleware  # noqa: PLC0415

        config = StripeSettings.load()
        config.secret_key = "sk_test_123"  # noqa: S105
        config.save()
        peer = make_peer()
        request = RequestFactory().post("/", {})
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        request.user = peer
        balance = SimpleNamespace(
            available=[{"amount": 100, "currency": "gbp"}],
            pending=[],
        )
        remote = SimpleNamespace(status=SubscriptionStatus.active)

        with (
            patch(
                "neuromancers_network.payments.services.stripe.Balance.retrieve",
                return_value=balance,
            ),
            patch(
                "neuromancers_network.payments.services.stripe.Subscription.retrieve",
                return_value=remote,
            ),
            patch(
                "neuromancers_network.payments.services.stripe.Subscription.cancel",
            ),
            patch(
                "neuromancers_network.payments.services.stripe.Account.delete",
            ) as delete_account,
        ):
            response = peer_stripe_disconnect(request, request.POST)

        assert response.status_code == HTTPStatus.FOUND
        assert any(
            "remaining funds" in str(message) for message in get_messages(request)
        )
        delete_account.assert_not_called()
        peer.payment_profile.refresh_from_db()
        assert peer.payment_profile.stripe_connect_account_id_id is not None


class TestPeerSubscribe:
    def test_disabled_setting_blocks_subscribe(self):
        config = StripeSettings.load()
        config.subscription_enabled = False
        config.save()
        peer = make_peer()

        with pytest.raises(PermissionDenied, match="disabled"):
            peer_subscribe(_post(peer), {})

    def test_requires_provider_agreement(self):
        config = StripeSettings.load()
        config.subscription_enabled = True
        config.save()
        peer = make_peer()

        with pytest.raises(PermissionDenied, match="provider agreement"):
            peer_subscribe(_post(peer), {})

    def test_starts_checkout_when_enabled_and_agreed(self):
        config = StripeSettings.load()
        config.subscription_enabled = True
        config.save()
        peer = make_peer(subscription_status=None)
        profile = peer.peer_profile
        profile.provider_agreement_accepted_at = timezone.now()
        profile.provider_agreement_version = PROVIDER_AGREEMENT_VERSION
        profile.save(
            update_fields=[
                "provider_agreement_accepted_at",
                "provider_agreement_version",
                "updated_at",
            ],
        )

        with (
            patch(
                "neuromancers_network.payments.services.create_subscription_checkout",
                return_value="https://checkout.example/session",
            ) as checkout,
            patch(
                "neuromancers_network.peers.actions.ensure_payment_profile",
            ),
        ):
            response = peer_subscribe(_post(peer), {})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "https://checkout.example/session"
        checkout.assert_called_once()


class TestConnectStripeRedirects:
    def _peer_with_agreement(self):
        peer = make_peer()
        peer_accept_provider_agreement(_post(peer), {})
        peer.payment_profile.stripe_connect_account_id = None
        peer.payment_profile.save(update_fields=["stripe_connect_account_id"])
        return peer

    def _link(self):
        profile = MagicMock()
        profile.create_stripe_onboarding_link.return_value = SimpleNamespace(
            url="https://connect.stripe.example/onboard",
        )
        return profile

    def test_configured_urls_win_over_request_data(self):
        config = StripeSettings.load()
        config.onboarding_redirect_url = "https://app.example/return"
        config.onboarding_refresh_url = "https://app.example/refresh"
        config.save()
        peer = self._peer_with_agreement()
        profile = self._link()

        with patch(
            "neuromancers_network.peers.actions.ensure_payment_profile",
            return_value=profile,
        ):
            response = peer_connect_stripe(
                _post(peer),
                {
                    "return_url": "https://evil.example/return",
                    "refresh_url": "https://evil.example/refresh",
                },
            )

        assert response.status_code == HTTPStatus.FOUND
        profile.create_stripe_onboarding_link.assert_called_once_with(
            refresh_url="https://app.example/refresh",
            return_url="https://app.example/return",
        )

    def test_external_urls_fall_back_to_the_profile(self):
        config = StripeSettings.load()
        config.onboarding_redirect_url = ""
        config.onboarding_refresh_url = ""
        config.save()
        peer = self._peer_with_agreement()
        profile = self._link()
        fallback = f"http://testserver{peer.get_absolute_url()}"

        with patch(
            "neuromancers_network.peers.actions.ensure_payment_profile",
            return_value=profile,
        ):
            peer_connect_stripe(
                _post(peer),
                {
                    "return_url": "https://evil.example/return",
                    "refresh_url": "https://evil.example/refresh",
                },
            )

        profile.create_stripe_onboarding_link.assert_called_once_with(
            refresh_url=fallback,
            return_url=fallback,
        )

    def test_same_host_relative_urls_are_accepted(self):
        config = StripeSettings.load()
        config.onboarding_redirect_url = ""
        config.onboarding_refresh_url = ""
        config.save()
        peer = self._peer_with_agreement()
        profile = self._link()

        with patch(
            "neuromancers_network.peers.actions.ensure_payment_profile",
            return_value=profile,
        ):
            peer_connect_stripe(
                _post(peer),
                {"return_url": "/settings/", "refresh_url": "/settings/stripe/"},
            )

        profile.create_stripe_onboarding_link.assert_called_once_with(
            refresh_url="http://testserver/settings/stripe/",
            return_url="http://testserver/settings/",
        )


class TestProviderAgreement:
    def test_accept_records_agreement(self):
        peer = make_peer()

        peer_accept_provider_agreement(_post(peer), {})

        profile = peer.peer_profile
        profile.refresh_from_db()
        assert profile.provider_agreement_accepted_at is not None
        assert profile.provider_agreement_version == PROVIDER_AGREEMENT_VERSION

    def test_connect_stripe_requires_agreement(self):
        peer = make_peer()

        with pytest.raises(PermissionDenied, match="provider agreement"):
            peer_connect_stripe(_post(peer), {})
