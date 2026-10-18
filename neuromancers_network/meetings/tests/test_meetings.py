from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.test import RequestFactory
from django.utils import timezone

from neuromancers_network.core.models import StripeSettings
from neuromancers_network.inbox.models import NotificationEventLog
from neuromancers_network.meetings.actions import bookings_approve
from neuromancers_network.meetings.actions import bookings_revoke
from neuromancers_network.meetings.actions import meetings_apply_terms_template
from neuromancers_network.meetings.actions import meetings_delete
from neuromancers_network.meetings.actions import refunds_approve
from neuromancers_network.meetings.forms_pages import MeetingEditFormPage
from neuromancers_network.meetings.models import ApprovalPolicy
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingPriceOption
from neuromancers_network.meetings.models import MeetingPriceTier
from neuromancers_network.meetings.models import MeetingRequestStatus
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.models import MeetingType
from neuromancers_network.meetings.models import PricingType
from neuromancers_network.meetings.models import RefundRequest
from neuromancers_network.meetings.models import RefundStatus
from neuromancers_network.meetings.selectors import my_meetings
from neuromancers_network.meetings.services import apply_duration_tiers
from neuromancers_network.meetings.services import cancel_and_refund_for_peer
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.services import create_meeting
from neuromancers_network.meetings.services import delete_all
from neuromancers_network.meetings.services import delete_meeting
from neuromancers_network.meetings.services import publish_meeting
from neuromancers_network.meetings.services import unpublish_all
from neuromancers_network.meetings.tests.factories import create_meeting as make_meeting
from neuromancers_network.meetings.tier_fields import DurationTiersField
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.taxonomy.tests.factories import AllowedTagFactory
from neuromancers_network.taxonomy.tests.factories import CountryFactory
from neuromancers_network.taxonomy.tests.factories import LanguageFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _request(user):
    request = RequestFactory().post("/", {})
    request.user = user
    return request


def meeting_fields() -> dict:
    return {
        "title": "Session",
        "description": "A test meeting",
        "meeting_type": MeetingType.ONE_ON_ONE,
        "pricing_type": PricingType.FIXED,
        "price": 25,
        "approval_policy": ApprovalPolicy.PAY_AFTER_JOIN,
        "currency": "GBP",
    }


class TestCreateMeeting:
    def test_ineligible_peer_is_rejected(self):
        peer = UserFactory()

        with pytest.raises(PermissionDenied):
            create_meeting(peer=peer, **meeting_fields())

    def test_eligible_peer_creates_draft_with_default_terms(self):
        peer = make_peer(default_terms="Be kind")

        meeting = create_meeting(peer=peer, **meeting_fields())

        assert meeting.status == MeetingStatus.DRAFT
        assert meeting.terms == "Be kind"

    def test_explicit_terms_are_kept(self):
        peer = make_peer(default_terms="Default")

        meeting = create_meeting(peer=peer, terms="Custom", **meeting_fields())

        assert meeting.terms == "Custom"


class TestCreateMeetingTaxonomy:
    def test_unknown_tag_is_rejected(self):
        peer = make_peer()

        with pytest.raises(ValidationError):
            create_meeting(peer=peer, tags=["unknown"], **meeting_fields())

    def test_inactive_tag_is_rejected(self):
        peer = make_peer()
        AllowedTagFactory(name="retired", is_active=False)

        with pytest.raises(ValidationError):
            create_meeting(peer=peer, tags=["retired"], **meeting_fields())

    def test_unknown_taxonomy_is_rejected(self):
        peer = make_peer()

        with pytest.raises(ValidationError):
            create_meeting(peer=peer, countries=["ZZ"], **meeting_fields())

        with pytest.raises(ValidationError):
            create_meeting(peer=peer, languages=["zz"], **meeting_fields())

    def test_valid_taxonomy_is_set(self):
        peer = make_peer()
        tag = AllowedTagFactory(name="anxiety")
        countries = [CountryFactory(), CountryFactory()]
        languages = [LanguageFactory(), LanguageFactory()]

        meeting = create_meeting(
            peer=peer,
            tags=[tag],
            countries=countries,
            languages=languages,
            **meeting_fields(),
        )

        assert list(meeting.tags.all()) == [tag]
        assert set(meeting.countries.all()) == set(countries)
        assert set(meeting.languages.all()) == set(languages)


class TestMeetingManageActions:
    def test_delete_requires_ownership(self):
        meeting = make_meeting(peer=make_peer())

        with pytest.raises(PermissionDenied):
            meetings_delete(_request(make_peer()), {"target": meeting.pk})

    def test_owner_can_delete(self):
        meeting = make_meeting(peer=make_peer())

        meetings_delete(_request(meeting.peer), {"target": meeting.pk})

        assert not type(meeting).objects.filter(pk=meeting.pk).exists()


class TestMyMeetings:
    def test_returns_only_signed_in_users_meetings(self):
        peer = make_peer()
        mine = make_meeting(peer=peer, title="Mine")
        make_meeting(peer=make_peer(), title="Theirs")

        results = my_meetings(request=_request(peer))

        assert list(results) == [mine]

    def test_anonymous_sees_nothing(self):
        make_meeting(peer=make_peer())
        anonymous = RequestFactory().get("/")
        anonymous.user = type("Anon", (), {"is_authenticated": False})()

        assert list(my_meetings(request=anonymous)) == []


class TestMeetingEditFormPage:
    def test_non_owner_cannot_update(self):
        meeting = make_meeting(peer=make_peer())
        page = MeetingEditFormPage()
        setattr(page, "_daisie_request", _request(make_peer()))  # noqa: B010

        assert page.update_instance_from_submission(object(), meeting) is None

    def test_anonymous_cannot_update(self):
        meeting = make_meeting(peer=make_peer())
        page = MeetingEditFormPage()
        setattr(page, "_daisie_request", None)  # noqa: B010

        assert page.update_instance_from_submission(object(), meeting) is None


def make_meeting_with_tiers():
    meeting = make_meeting(peer=UserFactory())
    tier = MeetingPriceTier.objects.create(meeting=meeting, duration_minutes=60)
    standard = MeetingPriceOption.objects.create(
        tier=tier,
        amount=Decimal("50.00"),
        label="Standard",
        is_default=True,
    )
    reduced = MeetingPriceOption.objects.create(
        tier=tier,
        amount=Decimal("30.00"),
        label="Reduced",
    )
    return meeting, tier, standard, reduced


class TestPriceOptions:
    def test_options_for_known_duration(self):
        meeting, _tier, standard, reduced = make_meeting_with_tiers()

        assert set(meeting.price_options_for(60)) == {standard, reduced}

    def test_options_for_unknown_duration_is_empty(self):
        meeting, _tier, _standard, _reduced = make_meeting_with_tiers()

        assert list(meeting.price_options_for(15)) == []


class TestPriceFor:
    def test_default_option_amount(self):
        meeting, _tier, _standard, _reduced = make_meeting_with_tiers()

        assert meeting.price_for(60) == Decimal("50.00")

    def test_specific_option_amount(self):
        meeting, _tier, _standard, reduced = make_meeting_with_tiers()

        assert meeting.price_for(60, option_id=reduced.pk) == Decimal("30.00")

    def test_unknown_option_returns_none(self):
        meeting, _tier, _standard, _reduced = make_meeting_with_tiers()

        assert meeting.price_for(60, option_id=99999) is None

    def test_unknown_duration_falls_back_to_meeting_price(self):
        meeting, _tier, _standard, _reduced = make_meeting_with_tiers()

        assert meeting.price_for(15) == meeting.price


class TestTierConstraints:
    def test_duplicate_duration_rejected(self):
        meeting = make_meeting(peer=UserFactory())
        MeetingPriceTier.objects.create(meeting=meeting, duration_minutes=30)

        with pytest.raises(IntegrityError), transaction.atomic():
            MeetingPriceTier.objects.create(meeting=meeting, duration_minutes=30)


class TestApplyDurationTiers:
    def test_creates_tiers_and_default_options(self):
        meeting = make_meeting(peer=UserFactory())

        apply_duration_tiers(
            meeting,
            [
                {"duration_minutes": 30, "amount": Decimal("20.00")},
                {"duration_minutes": 60, "amount": Decimal("35.00")},
            ],
        )

        assert set(meeting.price_tiers.values_list("duration_minutes", flat=True)) == {
            30,
            60,
        }
        assert meeting.price_for(30) == Decimal("20.00")
        assert meeting.price_for(60) == Decimal("35.00")

    def test_removes_stale_tiers(self):
        meeting = make_meeting(peer=UserFactory())
        MeetingPriceTier.objects.create(meeting=meeting, duration_minutes=15)

        apply_duration_tiers(
            meeting,
            [{"duration_minutes": 30, "amount": Decimal("10.00")}],
        )

        assert list(meeting.price_tiers.values_list("duration_minutes", flat=True)) == [
            30,
        ]

    def test_blank_amount_clears_options(self):
        meeting, _tier, _standard, _reduced = make_meeting_with_tiers()

        apply_duration_tiers(meeting, [{"duration_minutes": 60, "amount": None}])

        assert list(meeting.price_options_for(60)) == []


class TestDurationTiersField:
    def test_rejects_out_of_range_duration(self):
        with pytest.raises(ValidationError):
            DurationTiersField(required=False).clean(
                [{"duration_minutes": 3, "amount": ""}],
            )


def _accept_provider_agreement(peer):
    profile = peer.peer_profile
    profile.provider_agreement_accepted_at = timezone.now()
    profile.save(update_fields=["provider_agreement_accepted_at", "updated_at"])


class TestPublishMeeting:
    def test_requires_terms(self):
        peer = make_peer()
        _accept_provider_agreement(peer)
        meeting = make_meeting(peer=peer, status=MeetingStatus.DRAFT)

        with pytest.raises(ValidationError, match="terms"):
            publish_meeting(meeting)

    def test_requires_provider_agreement(self):
        peer = make_peer()
        meeting = make_meeting(peer=peer, status=MeetingStatus.DRAFT)
        meeting.terms = "Terms"
        meeting.save()

        with pytest.raises(PermissionDenied, match="provider agreement"):
            publish_meeting(meeting)

    def test_publishes_when_ready(self):
        peer = make_peer()
        _accept_provider_agreement(peer)
        meeting = make_meeting(peer=peer, status=MeetingStatus.DRAFT)
        meeting.terms = "Terms"
        meeting.save()

        publish_meeting(meeting)

        meeting.refresh_from_db()
        assert meeting.status == MeetingStatus.PUBLISHED


class TestApplyTermsTemplate:
    def test_applies_template_body(self):
        peer = make_peer()
        profile = peer.peer_profile
        profile.terms_templates = [{"name": "Standard", "body": "Template body"}]
        profile.save(update_fields=["terms_templates", "updated_at"])
        meeting = make_meeting(peer=peer, status=MeetingStatus.DRAFT)

        meetings_apply_terms_template(
            _request(peer),
            {"target": meeting.pk, "template": "Standard"},
        )

        meeting.refresh_from_db()
        assert meeting.terms == "Template body"


def _pending_request(peer):
    meeting = make_meeting(peer=peer, status=MeetingStatus.PUBLISHED)
    meeting.approval_policy = ApprovalPolicy.APPROVAL_REQUIRED
    meeting.save()
    booking = create_booking(
        meeting=meeting,
        seeker=UserFactory(),
        sessions=[{"requested_duration_minutes": 30}],
    )
    return booking.sessions.first()


def _paid_request(peer, *, refund_requires_approval=True):
    meeting_request = _pending_request(peer)
    meeting_request.__dict__["status"] = MeetingRequestStatus.PAID
    meeting_request.stripe_payment_intent_id = "pi_host"
    meeting_request.save()
    meeting = meeting_request.meeting
    meeting.refund_requires_approval = refund_requires_approval
    meeting.save()
    return meeting_request


class TestHostActions:
    def test_non_host_cannot_approve(self):
        meeting_request = _pending_request(make_peer())

        with pytest.raises(PermissionDenied):
            bookings_approve(_request(make_peer()), {"target": meeting_request.pk})

    def test_revoke_paid_request_raises_refund(self):
        peer = make_peer()
        meeting_request = _paid_request(peer)

        bookings_revoke(_request(peer), {"target": meeting_request.pk})

        meeting_request.refresh_from_db()
        assert meeting_request.status == MeetingRequestStatus.CANCELLED
        assert RefundRequest.objects.filter(meeting_request=meeting_request).exists()

    def test_refunds_approve_issues_refund(self):
        config = StripeSettings.load()
        config.secret_key = "sk_test_123"  # noqa: S105
        config.save()
        peer = make_peer()
        meeting_request = _paid_request(peer)
        refund = meeting_request.request_refund("Please")

        with (
            patch(
                "neuromancers_network.meetings.models.refund.stripe.Refund.create",
            ) as create_refund,
            patch(
                "neuromancers_network.meetings.models.refund."
                "StripeRefund.sync_from_stripe_data",
            ),
        ):
            create_refund.return_value = type("Refund", (), {"id": "re_host"})()
            refunds_approve(_request(peer), {"target": refund.pk})

        refund.refresh_from_db()
        assert refund.status == RefundStatus.APPROVED
        assert refund.stripe_refund_id == "re_host"


class TestBulkMeetingServices:
    def test_unpublish_all_only_published_of_peer(self):
        peer = make_peer()
        published = make_meeting(peer=peer, title="A", status=MeetingStatus.PUBLISHED)
        draft = make_meeting(peer=peer, title="B", status=MeetingStatus.DRAFT)
        other = make_meeting(
            peer=make_peer(),
            title="C",
            status=MeetingStatus.PUBLISHED,
        )

        count = unpublish_all(peer)

        published.refresh_from_db()
        draft.refresh_from_db()
        other.refresh_from_db()
        assert count == 1
        assert published.status == MeetingStatus.DRAFT
        assert draft.status == MeetingStatus.DRAFT
        assert other.status == MeetingStatus.PUBLISHED

    def test_delete_all_scoped_to_peer(self):
        peer = make_peer()
        make_meeting(peer=peer, title="A")
        make_meeting(peer=peer, title="B")
        make_meeting(peer=make_peer(), title="C")

        deleted = delete_all(peer)

        assert deleted == 2  # noqa: PLR2004
        assert not Meeting.objects.filter(peer=peer).exists()

    def test_cancel_and_refund_peer_bookings(self):
        peer = make_peer()
        paid = _paid_request(peer, refund_requires_approval=True)

        cancelled = cancel_and_refund_for_peer(peer)

        paid.refresh_from_db()
        assert cancelled == 1
        assert paid.status == MeetingRequestStatus.CANCELLED
        assert RefundRequest.objects.filter(meeting_request=paid).exists()


class TestMeetingDeletion:
    def test_delete_meeting_cancels_and_notifies(self):
        peer = make_peer()
        request = _paid_request(peer, refund_requires_approval=True)
        meeting = request.meeting

        delete_meeting(meeting)

        assert not Meeting.objects.filter(pk=meeting.pk).exists()
        assert NotificationEventLog.objects.filter(
            event_type="booking_cancelled",
            event_ref=f"meetingrequest.{request.pk}.cancel",
        ).exists()

    def test_delete_meeting_refunds_paid_request(self):
        config = StripeSettings.load()
        config.secret_key = "sk_test_123"  # noqa: S105
        config.charge_type = StripeSettings.ChargeType.DESTINATION
        config.save()
        peer = make_peer()
        request = _paid_request(peer, refund_requires_approval=False)
        meeting = request.meeting

        with (
            patch(
                "neuromancers_network.meetings.models.refund.stripe.Refund.create",
            ) as create_refund,
            patch(
                "neuromancers_network.meetings.models.refund."
                "StripeRefund.sync_from_stripe_data",
            ),
        ):
            create_refund.return_value = SimpleNamespace(id="re_delete")
            delete_meeting(meeting)

        assert not Meeting.objects.filter(pk=meeting.pk).exists()
        assert NotificationEventLog.objects.filter(
            event_type="refund_refunded",
            payload__meta__meeting_request_id=request.pk,
        ).exists()

    def test_delete_all_cancels_active_requests(self):
        peer = make_peer()
        request = _paid_request(peer, refund_requires_approval=True)

        delete_all(peer)

        assert not Meeting.objects.filter(peer=peer).exists()
        assert NotificationEventLog.objects.filter(
            event_type="booking_cancelled",
            event_ref=f"meetingrequest.{request.pk}.cancel",
        ).exists()


class TestMeetingSchedulingWindow:
    def _group(self, *, scheduled_at):
        meeting = Meeting(
            peer=make_peer(),
            title="Scheduling window",
            description="Test",
            meeting_type=MeetingType.GROUP,
            pricing_type=PricingType.FIXED,
            price=5,
            approval_policy=ApprovalPolicy.PAY_AFTER_JOIN,
            currency="GBP",
            scheduled_at=scheduled_at,
            duration_minutes=60,
            max_participants=5,
            status=MeetingStatus.DRAFT,
        )
        meeting.save(validate=False)
        return meeting

    def test_editing_within_window_is_allowed(self):
        meeting = self._group(scheduled_at=timezone.now() + timedelta(days=1))
        Meeting.objects.filter(pk=meeting.pk).update(
            scheduled_at=timezone.now() + timedelta(minutes=10),
        )
        meeting.refresh_from_db()

        meeting.description = "Updated description"
        meeting.save()

        meeting.refresh_from_db()
        assert meeting.description == "Updated description"

    def test_moving_schedule_into_window_is_rejected(self):
        meeting = self._group(scheduled_at=timezone.now() + timedelta(days=1))
        meeting.scheduled_at = timezone.now() + timedelta(minutes=10)

        with pytest.raises(ValidationError, match="at least 30 minutes"):
            meeting.save()

    def test_publishing_within_window_is_rejected(self):
        meeting = self._group(scheduled_at=timezone.now() + timedelta(minutes=10))
        meeting.publish()

        with pytest.raises(ValidationError, match="at least 30 minutes"):
            meeting.save(update_fields=["status", "updated_at"])
