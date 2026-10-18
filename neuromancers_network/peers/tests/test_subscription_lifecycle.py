"""Subscription lifecycle: pause/resume/cancel, eligibility and webhooks."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone

from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.payments import services as payment_services
from neuromancers_network.peers import signals
from neuromancers_network.peers.actions import peer_subscription_pause
from neuromancers_network.peers.models.settings import PeerRequirementsSettings
from neuromancers_network.peers.services import is_eligible_peer
from neuromancers_network.peers.tests.factories import make_peer

pytestmark = pytest.mark.django_db

_DUMMY_STRIPE_VALUE = "sk_test"


def _settings_stub():
    return SimpleNamespace(secret_key=_DUMMY_STRIPE_VALUE)


def _fresh(user):
    return get_user_model().objects.get(pk=user.pk)


class TestPausedEligibility:
    def test_paused_peer_is_ineligible(self):
        peer = make_peer()
        peer_subscription = peer.payment_profile.peer_subscription
        peer_subscription.paused_at = timezone.now()
        peer_subscription.save(update_fields=["paused_at"])

        assert is_eligible_peer(_fresh(peer)) is False

    def test_unpaused_peer_is_eligible(self):
        peer = make_peer()

        assert is_eligible_peer(_fresh(peer)) is True


class TestSubscriptionServices:
    def _profile(self):
        return make_peer().payment_profile

    @pytest.fixture(autouse=True)
    def _stripe_settings(self, monkeypatch):
        monkeypatch.setattr(
            payment_services.StripeSettings,
            "load",
            classmethod(lambda cls, request=None: _settings_stub()),
        )

    def test_pause_uses_pause_collection(self, monkeypatch):
        profile = self._profile()
        calls = {}
        monkeypatch.setattr(
            payment_services.stripe.Subscription,
            "modify",
            lambda sub_id, **kwargs: calls.update(sub_id=sub_id, kwargs=kwargs),
        )

        payment_services.pause_subscription(profile)

        assert calls["sub_id"] == profile.peer_subscription.subscription_id
        assert calls["kwargs"]["pause_collection"] == {"behavior": "void"}
        profile.peer_subscription.refresh_from_db()
        assert profile.peer_subscription.paused_at is not None

    def test_resume_resets_billing_anchor(self, monkeypatch):
        profile = self._profile()
        peer_subscription = profile.peer_subscription
        peer_subscription.paused_at = timezone.now()
        peer_subscription.save(update_fields=["paused_at"])
        calls = {}
        monkeypatch.setattr(
            payment_services.stripe.Subscription,
            "resume",
            lambda sub_id, **kwargs: calls.update(sub_id=sub_id, kwargs=kwargs),
        )

        payment_services.resume_subscription(profile)

        assert calls["kwargs"]["billing_cycle_anchor"] == "now"
        assert calls["kwargs"]["proration_behavior"] == "create_prorations"
        peer_subscription.refresh_from_db()
        assert peer_subscription.paused_at is None

    def test_cancel_at_period_end_modifies(self, monkeypatch):
        profile = self._profile()
        calls = {}
        monkeypatch.setattr(
            payment_services.stripe.Subscription,
            "modify",
            lambda sub_id, **kwargs: calls.update(kwargs=kwargs),
        )

        payment_services.cancel_subscription(profile, at_period_end=True)

        assert calls["kwargs"]["cancel_at_period_end"] is True

    def test_cancel_immediately_cancels(self, monkeypatch):
        profile = self._profile()
        calls = {}
        monkeypatch.setattr(
            payment_services.stripe.Subscription,
            "cancel",
            lambda sub_id: calls.update(sub_id=sub_id),
        )

        payment_services.cancel_subscription(profile, at_period_end=False)

        assert calls["sub_id"] == profile.peer_subscription.subscription_id


class TestPauseWebhook:
    def _event(self, peer, *, pause_collection, status="active"):
        return SimpleNamespace(
            type="customer.subscription.updated",
            data={
                "object": {
                    "id": peer.payment_profile.peer_subscription.subscription_id,
                    "customer": peer.payment_profile.stripe_customer_id_id,
                    "status": status,
                    "pause_collection": pause_collection,
                    "items": {"data": [{"price": {"id": "price_test"}}]},
                },
            },
            default_api_key="sk_test",
        )

    @pytest.fixture(autouse=True)
    def _peer_plan(self):
        requirements = PeerRequirementsSettings.load()
        requirements.peer_plan_price_ids = ["price_test"]
        requirements.save()

    def _patch_sync(self, monkeypatch, peer):
        subscription = peer.payment_profile.peer_subscription.subscription
        monkeypatch.setattr(
            signals.StripeSubscription,
            "sync_from_stripe_data",
            lambda data, api_key=None: subscription,
        )

    def test_updated_with_pause_marks_paused_and_lapses(self, monkeypatch):
        peer = make_peer()
        meeting = create_meeting(peer=peer)
        self._patch_sync(monkeypatch, peer)

        signals.sync_peer_subscription(
            sender=None,
            event=self._event(peer, pause_collection={"behavior": "void"}),
        )

        subscription = peer.payment_profile.peer_subscription
        subscription.refresh_from_db()
        assert subscription.paused_at is not None
        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.DRAFT

    @pytest.mark.parametrize("lapsed_status", ["past_due", "unpaid"])
    def test_updated_lapsed_status_unpublishes(self, monkeypatch, lapsed_status):
        peer = make_peer()
        meeting = create_meeting(peer=peer)
        self._patch_sync(monkeypatch, peer)

        signals.sync_peer_subscription(
            sender=None,
            event=self._event(
                peer,
                pause_collection=None,
                status=lapsed_status,
            ),
        )

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.DRAFT

    def test_updated_without_pause_clears_paused(self, monkeypatch):
        peer = make_peer()
        subscription = peer.payment_profile.peer_subscription
        subscription.paused_at = timezone.now()
        subscription.save(update_fields=["paused_at"])
        self._patch_sync(monkeypatch, peer)

        signals.sync_peer_subscription(
            sender=None,
            event=self._event(peer, pause_collection=None),
        )

        subscription.refresh_from_db()
        assert subscription.paused_at is None


class TestPauseAction:
    def test_pause_action_calls_service(self, monkeypatch):
        peer = make_peer()
        profile = peer.peer_profile
        profile.provider_agreement_accepted_at = timezone.now()
        profile.save(update_fields=["provider_agreement_accepted_at"])

        called = {}
        monkeypatch.setattr(
            payment_services,
            "pause_subscription",
            lambda payment_profile: called.setdefault("profile", payment_profile),
        )

        request = RequestFactory().post("/")
        request.user = peer
        peer_subscription_pause(request, {})

        assert called["profile"].pk == peer.payment_profile.pk
