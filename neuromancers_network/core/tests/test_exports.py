from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from neuromancers_network.core.currency import convert_amount
from neuromancers_network.core.i18n import bust_localization_cache
from neuromancers_network.core.ical import build_ics
from neuromancers_network.core.models import LocalizationSettings
from neuromancers_network.meetings.services import create_booking
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.tests.factories import make_peer
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

SESSION_DURATION = 30


def configure(**kwargs):
    config = LocalizationSettings.load()
    for field, value in kwargs.items():
        setattr(config, field, value)
    config.save()
    bust_localization_cache()


def make_booking_with_session():
    return create_booking(
        meeting=create_meeting(peer=make_peer()),
        seeker=UserFactory(),
        sessions=[
            {
                "requested_start_time": timezone.now() + timedelta(hours=24),
                "requested_duration_minutes": SESSION_DURATION,
            },
        ],
    )


class TestConvertAmount:
    def test_same_currency_unchanged(self):
        configure(display_currency="GBP")

        assert convert_amount(Decimal("10.00"), source_currency="GBP") == Decimal(
            "10.00",
        )

    def test_stripe_source_unchanged(self):
        configure(display_currency="EUR", exchange_rate_source="stripe")

        assert convert_amount(Decimal("10.00"), source_currency="GBP") == Decimal(
            "10.00",
        )

    def test_manual_rate_applied(self):
        configure(
            display_currency="EUR",
            exchange_rate_source="manual",
            manual_exchange_rates={"EUR": "1.2"},
        )

        assert convert_amount(Decimal("10.00"), source_currency="GBP") == Decimal(
            "12.00",
        )

    def test_missing_rate_falls_back(self):
        configure(
            display_currency="EUR",
            exchange_rate_source="manual",
            manual_exchange_rates={},
        )

        assert convert_amount(Decimal("10.00"), source_currency="GBP") == Decimal(
            "10.00",
        )


class TestBuildIcs:
    def test_contains_calendar_and_event(self):
        booking = make_booking_with_session()

        text = build_ics([booking]).decode()

        assert "BEGIN:VCALENDAR" in text
        assert "BEGIN:VEVENT" in text
        assert "SUMMARY:Meeting" in text
        assert f"booking-{booking.pk}-session-{booking.sessions.first().pk}" in text
