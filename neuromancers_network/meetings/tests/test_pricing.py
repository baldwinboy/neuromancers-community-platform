from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.http import QueryDict

from neuromancers_network.meetings.models import MeetingPriceOption
from neuromancers_network.meetings.models import MeetingPriceTier
from neuromancers_network.meetings.services import apply_duration_tiers
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.meetings.tier_fields import DurationTiersField
from neuromancers_network.meetings.tier_fields import DurationTiersWidget
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


class TestApplyDurationTiers:
    def test_creates_tiers_and_default_options(self):
        meeting = create_meeting(peer=UserFactory())

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
        meeting = create_meeting(peer=UserFactory())
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
    def test_widget_parses_rows(self):
        data = QueryDict(
            "tiers-duration=30&tiers-duration=60&tiers-amount=20&tiers-amount=35",
        )

        raw = DurationTiersWidget().value_from_datadict(data, {}, "tiers")
        cleaned = DurationTiersField(required=False).clean(raw)

        assert [row["duration_minutes"] for row in cleaned] == [30, 60]
        assert cleaned[0]["amount"] == Decimal("20")

    def test_rejects_out_of_range_duration(self):
        with pytest.raises(ValidationError):
            DurationTiersField(required=False).clean(
                [{"duration_minutes": 3, "amount": ""}],
            )

    def test_skips_blank_rows(self):
        assert (
            DurationTiersField(required=False).clean(
                [{"duration_minutes": "", "amount": ""}],
            )
            == []
        )
