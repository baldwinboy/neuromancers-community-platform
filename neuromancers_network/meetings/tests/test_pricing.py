from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.db import transaction

from neuromancers_network.meetings.models import MeetingPriceOption
from neuromancers_network.meetings.models import MeetingPriceTier
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def make_meeting_with_tiers():
    meeting = create_meeting(peer=UserFactory())
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
        meeting = create_meeting(peer=UserFactory())
        MeetingPriceTier.objects.create(meeting=meeting, duration_minutes=30)

        with pytest.raises(IntegrityError), transaction.atomic():
            MeetingPriceTier.objects.create(meeting=meeting, duration_minutes=30)
