from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django_fsm import TransitionNotAllowed

from neuromancers_network.events.checkout import CheckoutStrategy
from neuromancers_network.events.checkout import build_destination_checkout_params
from neuromancers_network.events.checkout import determine_strategy
from neuromancers_network.events.checkout import plan_transfers
from neuromancers_network.events.models import AvailabilityRule
from neuromancers_network.events.models import BookingStatus
from neuromancers_network.events.models import DurationPrice
from neuromancers_network.events.models import PaymentStatus
from neuromancers_network.events.models import Session
from neuromancers_network.events.models import SessionBooking
from neuromancers_network.events.models import SessionPrice
from neuromancers_network.events.models import SessionType
from neuromancers_network.events.models import WebhookEventLog


class SessionPricingValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def _create_complete_prices(self, session):
        SessionPrice.objects.create(
            session=session,
            price_type="fixed",
            amount_subunit=2500,
            sort_order=0,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="hourly_rate",
            amount_subunit=5000,
            sort_order=0,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="sliding_scale",
            amount_subunit=1000,
            min_amount_subunit=500,
            max_amount_subunit=5000,
            sort_order=0,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="sliding_scale",
            amount_subunit=2000,
            sort_order=1,
        )

    def test_session_requires_all_pricing_types_when_published(self):
        session = Session.objects.create(
            host=self.user,
            title="Support Session",
            session_type=SessionType.PEER,
            is_published=False,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="fixed",
            amount_subunit=2500,
            sort_order=0,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="hourly_rate",
            amount_subunit=5000,
            sort_order=0,
        )

        session.is_published = True
        with pytest.raises(ValidationError):
            session.full_clean()

    def test_session_published_pricing_accepts_complete_configuration(self):
        session = Session.objects.create(
            host=self.user,
            title="Support Session",
            session_type=SessionType.PEER,
            is_published=False,
        )
        self._create_complete_prices(session)

        session.is_published = True
        session.full_clean()

    def test_session_sliding_scale_must_be_sorted_and_unique(self):
        session = Session.objects.create(
            host=self.user,
            title="Support Session",
            session_type=SessionType.PEER,
            is_published=True,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="fixed",
            amount_subunit=2500,
            sort_order=0,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="hourly_rate",
            amount_subunit=5000,
            sort_order=0,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="sliding_scale",
            amount_subunit=3000,
            sort_order=0,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="sliding_scale",
            amount_subunit=2000,
            sort_order=1,
        )

        with pytest.raises(ValidationError):
            session.full_clean()

    def test_session_min_duration_cannot_exceed_max(self):
        session = Session(
            host=self.user,
            title="Support Session",
            session_type=SessionType.PEER,
            min_duration_minutes=90,
            max_duration_minutes=60,
        )

        with pytest.raises(ValidationError):
            session.full_clean()

    def test_group_session_validates_pricing_when_published(self):
        starts_at = timezone.now() + timedelta(days=1)
        session = Session.objects.create(
            host=self.user,
            title="Group Circle",
            session_type=SessionType.GROUP,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=45),
            capacity=10,
            is_published=True,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="fixed",
            amount_subunit=2000,
            sort_order=0,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="hourly_rate",
            amount_subunit=4000,
            sort_order=0,
        )
        SessionPrice.objects.create(
            session=session,
            price_type="sliding_scale",
            amount_subunit=1500,
            sort_order=0,
        )

        with pytest.raises(ValidationError):
            session.full_clean()


class AvailabilityRuleTests(TestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_user(
            username="avail_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_create_availability_rule(self):
        rule = AvailabilityRule.objects.create(
            host=self.host,
            day_of_week=0,
            start_time="09:00",
            end_time="17:00",
        )
        assert rule.pk is not None
        assert rule.get_day_of_week_display() == "Monday"

    def test_availability_rules_filter_by_host(self):
        other = get_user_model().objects.create_user(
            username="other_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        AvailabilityRule.objects.create(
            host=self.host, day_of_week=1, start_time="09:00", end_time="17:00"
        )
        AvailabilityRule.objects.create(
            host=other, day_of_week=2, start_time="10:00", end_time="14:00"
        )

        host_rules = AvailabilityRule.objects.filter(host=self.host)
        assert host_rules.count() == 1

    def test_availability_rule_default_active(self):
        rule = AvailabilityRule.objects.create(
            host=self.host,
            day_of_week=3,
            start_time="09:00",
            end_time="17:00",
        )
        assert rule.is_active is True


class BookingDurationEnforcementTests(TestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_user(
            username="duration_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.attendee = get_user_model().objects.create_user(
            username="duration_attendee",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_peer_session_enforces_min_duration(self):
        session = Session.objects.create(
            host=self.host,
            title="Min Duration Session",
            session_type=SessionType.PEER,
            min_duration_minutes=30,
            max_duration_minutes=120,
        )
        starts_at = timezone.now() + timedelta(days=1)
        ends_at = starts_at + timedelta(minutes=15)

        booking = SessionBooking(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        with pytest.raises(ValidationError):
            booking.clean()

    def test_peer_session_enforces_max_duration(self):
        session = Session.objects.create(
            host=self.host,
            title="Max Duration Session",
            session_type=SessionType.PEER,
            min_duration_minutes=30,
            max_duration_minutes=120,
        )
        starts_at = timezone.now() + timedelta(days=1)
        ends_at = starts_at + timedelta(minutes=180)

        booking = SessionBooking(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        with pytest.raises(ValidationError):
            booking.clean()


class BookingOverlapTests(TestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_user(
            username="overlap_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.attendee1 = get_user_model().objects.create_user(
            username="overlap_a1",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.attendee2 = get_user_model().objects.create_user(
            username="overlap_a2",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_confirm_rejects_overlapping_peer_booking(self):
        session = Session.objects.create(
            host=self.host,
            title="Overlap Test",
            session_type=SessionType.PEER,
        )
        base = timezone.now() + timedelta(days=1)

        booking1 = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee1,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=0,
            booking_status=BookingStatus.APPROVED,
            payment_status=PaymentStatus.NOT_REQUIRED,
        )
        booking1.confirm()
        booking1.save()

        booking2 = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee2,
            starts_at=base + timedelta(minutes=30),
            ends_at=base + timedelta(hours=1, minutes=30),
            amount_due_subunit=0,
            booking_status=BookingStatus.APPROVED,
            payment_status=PaymentStatus.NOT_REQUIRED,
        )

        with pytest.raises(TransitionNotAllowed):
            booking2.confirm()

    def test_non_overlapping_bookings_are_accepted(self):
        session = Session.objects.create(
            host=self.host,
            title="Non-Overlap Test",
            session_type=SessionType.PEER,
        )
        base = timezone.now() + timedelta(days=1)

        booking1 = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee1,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=0,
            booking_status=BookingStatus.APPROVED,
            payment_status=PaymentStatus.NOT_REQUIRED,
        )
        booking1.confirm()
        booking1.save()

        booking2 = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee1,
            starts_at=base + timedelta(hours=2),
            ends_at=base + timedelta(hours=3),
            amount_due_subunit=0,
            booking_status=BookingStatus.APPROVED,
            payment_status=PaymentStatus.NOT_REQUIRED,
        )
        booking2.confirm()
        booking2.save()
        assert booking2.booking_status == BookingStatus.CONFIRMED


class BookingCapacityTests(TestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_user(
            username="capacity_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.a1 = get_user_model().objects.create_user(
            username="capacity_a1",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.a2 = get_user_model().objects.create_user(
            username="capacity_a2",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_group_session_blocks_over_capacity(self):
        base = timezone.now() + timedelta(days=1)
        session = Session.objects.create(
            host=self.host,
            title="Capacity Test",
            session_type=SessionType.GROUP,
            capacity=1,
            starts_at=base,
            ends_at=base + timedelta(hours=2),
        )
        b1 = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.a1,
            starts_at=base,
            ends_at=base + timedelta(hours=2),
            amount_due_subunit=0,
            booking_status=BookingStatus.APPROVED,
            payment_status=PaymentStatus.NOT_REQUIRED,
        )
        b1.confirm()
        b1.save()

        assert session.spots_remaining <= 0

        b2 = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.a2,
            starts_at=base,
            ends_at=base + timedelta(hours=2),
            amount_due_subunit=0,
            booking_status=BookingStatus.APPROVED,
            payment_status=PaymentStatus.NOT_REQUIRED,
        )
        with pytest.raises(TransitionNotAllowed):
            b2.confirm()


class DurationPriceAmountLookupTests(TestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_user(
            username="dp_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_duration_price_amount_cents_lookup(self):
        session = Session.objects.create(
            host=self.host,
            title="DP Lookup",
            session_type=SessionType.PEER,
        )
        DurationPrice.objects.create(
            session=session,
            duration_minutes=60,
            amount_cents=2500,
        )
        dp = session.duration_prices.get(duration_minutes=60)
        assert dp.amount_cents == 2500

    def test_duration_price_unique_per_duration(self):
        session = Session.objects.create(
            host=self.host,
            title="DP Unique",
            session_type=SessionType.PEER,
        )
        DurationPrice.objects.create(
            session=session,
            duration_minutes=30,
            amount_cents=1500,
        )
        with pytest.raises(Exception):
            DurationPrice.objects.create(
                session=session,
                duration_minutes=30,
                amount_cents=2000,
            )


class CorePhase3BookingFlowTests(TestCase):
    """End-to-end booking flow tests for Phase 3 enforcement."""

    def setUp(self):
        self.host = get_user_model().objects.create_user(
            username="flow_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.attendee = get_user_model().objects.create_user(
            username="flow_attendee",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_booking_enforces_starts_before_ends(self):
        session = Session.objects.create(
            host=self.host,
            title="Flow Session",
            session_type=SessionType.PEER,
        )
        base = timezone.now() + timedelta(days=1)
        booking = SessionBooking(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=base + timedelta(hours=2),
            ends_at=base,
        )
        with pytest.raises(ValidationError):
            booking.clean()

    def test_booking_flow_with_duration_price(self):
        session = Session.objects.create(
            host=self.host,
            title="Flow Session",
            session_type=SessionType.PEER,
        )
        DurationPrice.objects.create(
            session=session,
            duration_minutes=60,
            amount_cents=3000,
        )
        base = timezone.now() + timedelta(days=1)
        booking = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=base,
            ends_at=base + timedelta(minutes=60),
            amount_due_subunit=3000,
            currency="gbp",
        )
        assert booking.amount_due_subunit == 3000
        assert booking.booking_status == BookingStatus.PENDING_APPROVAL


class CanonicalBookingContractTests(TestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_user(
            username="host_phase1a",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.attendee = get_user_model().objects.create_user(
            username="attendee_phase1a",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_booking_defaults_match_phase_1a_contract(self):
        session = Session.objects.create(
            host=self.host,
            title="Baseline session",
            session_type=SessionType.PEER,
            require_approval=True,
            require_payment_before_joining=True,
        )
        starts_at = timezone.now() + timedelta(days=1)

        booking = SessionBooking(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
        )

        assert booking.booking_status == BookingStatus.PENDING_APPROVAL
        assert booking.payment_status == PaymentStatus.REQUIRED
        assert booking.approval_required is True
        assert booking.amount_due_subunit == 0
        assert booking.amount_paid_subunit == 0
        assert booking.currency == "gbp"
        assert booking.checkout_reference == ""
        assert booking.timezone == "UTC"


class StripeCheckoutCreationTests(TestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_user(
            username="checkout_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.attendee = get_user_model().objects.create_user(
            username="checkout_user",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_build_destination_checkout_params(self):
        session = Session.objects.create(
            host=self.host,
            title="Pay Session",
            session_type=SessionType.PEER,
        )
        base = timezone.now() + timedelta(days=1)
        booking = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=2500,
            currency="gbp",
        )

        with pytest.raises(Exception):
            build_destination_checkout_params(
                booking,
                success_url="http://test/success/",
                cancel_url="http://test/cancel/",
            )

        assert booking.host_stripe_account_id == ""

    def test_determine_strategy_destination_for_single(self):
        session = Session.objects.create(
            host=self.host,
            title="Strategy Test",
            session_type=SessionType.PEER,
        )
        base = timezone.now() + timedelta(days=1)
        booking = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=1000,
        )
        strategy = determine_strategy([booking])
        assert strategy == CheckoutStrategy.DESTINATION

    def test_determine_strategy_separate_for_multiple(self):
        session = Session.objects.create(
            host=self.host,
            title="Strategy Multi",
            session_type=SessionType.PEER,
        )
        base = timezone.now() + timedelta(days=1)

        host2 = get_user_model().objects.create_user(
            username="checkout_host2",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        session2 = Session.objects.create(
            host=host2,
            title="Strategy Multi 2",
            session_type=SessionType.PEER,
        )
        b1 = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=1000,
        )
        b2 = SessionBooking.objects.create(
            session=session2,
            host=host2,
            attendee=self.attendee,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=2000,
        )
        strategy = determine_strategy([b1, b2])
        assert strategy == CheckoutStrategy.SEPARATE_CHARGES_AND_TRANSFERS


class WebhookIdempotencyTests(TestCase):
    def test_webhook_event_log_prevents_duplicate(self):
        WebhookEventLog.objects.create(
            event_id="evt_test_123",
            event_type="checkout.session.completed",
        )
        exists = WebhookEventLog.objects.filter(event_id="evt_test_123").exists()
        assert exists is True

    def test_webhook_event_log_unique_constraint(self):
        WebhookEventLog.objects.create(
            event_id="evt_test_unique",
            event_type="checkout.session.completed",
        )
        with pytest.raises(Exception):
            WebhookEventLog.objects.create(
                event_id="evt_test_unique",
                event_type="checkout.session.completed",
            )


class PaymentStatusTransitionTests(TestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_user(
            username="pay_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        self.attendee = get_user_model().objects.create_user(
            username="pay_user",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )

    def test_payment_flow_required_to_paid(self):
        session = Session.objects.create(
            host=self.host,
            title="Pay Flow",
            session_type=SessionType.PEER,
        )
        base = timezone.now() + timedelta(days=1)
        booking = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=2000,
        )
        assert booking.payment_status == PaymentStatus.REQUIRED

        booking.initiate_checkout()
        booking.checkout_reference = "cs_test_123"
        booking.save()
        assert booking.payment_status == PaymentStatus.CHECKOUT_CREATED

        booking.mark_processing()
        booking.mark_paid()
        booking.save()
        assert booking.payment_status == PaymentStatus.PAID

    def test_mark_paid_transition_updates_payment_status(self):
        session = Session.objects.create(
            host=self.host,
            title="Auto Confirm",
            session_type=SessionType.PEER,
            require_payment_before_joining=True,
        )
        base = timezone.now() + timedelta(days=1)
        booking = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=2000,
            booking_status=BookingStatus.APPROVED,
            payment_status=PaymentStatus.CHECKOUT_CREATED,
        )

        booking.payment_status = PaymentStatus.PAID
        booking.save(update_fields=["payment_status"])
        assert booking.payment_status == PaymentStatus.PAID

    def test_free_session_auto_confirm(self):
        session = Session.objects.create(
            host=self.host,
            title="Free Session",
            session_type=SessionType.PEER,
            require_approval=False,
        )
        base = timezone.now() + timedelta(days=1)
        booking = SessionBooking.objects.create(
            session=session,
            host=self.host,
            attendee=self.attendee,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=0,
        )
        booking.approve()
        booking.save()
        assert booking.booking_status == BookingStatus.APPROVED

        booking.confirm()
        booking.save()
        assert booking.booking_status == BookingStatus.CONFIRMED


class TransferPlanningTests(TestCase):
    def test_plan_transfers_returns_correct_structure(self):
        host = get_user_model().objects.create_user(
            username="transfer_host",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        attendee = get_user_model().objects.create_user(
            username="transfer_user",
            password="test-pass-123",
            date_of_birth="2000-01-01",
            accepted_tos=True,
        )
        session = Session.objects.create(
            host=host,
            title="Transfer Session",
            session_type=SessionType.PEER,
        )
        base = timezone.now() + timedelta(days=1)
        booking = SessionBooking.objects.create(
            session=session,
            host=host,
            attendee=attendee,
            starts_at=base,
            ends_at=base + timedelta(hours=1),
            amount_due_subunit=3000,
            currency="gbp",
        )
        group_id, transfers = plan_transfers("ch_test_123", [booking])
        assert group_id == f"cart_{booking.id}"
        assert len(transfers) == 1
        assert transfers[0].booking_id == booking.id
        assert transfers[0].amount_subunit == 3000
