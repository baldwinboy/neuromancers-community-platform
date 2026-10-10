from decimal import Decimal

import pytest
from django.http import QueryDict
from django.test import Client

from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import MeetingPriceOption
from neuromancers_network.meetings.models import MeetingPriceTier
from neuromancers_network.meetings.models import MeetingStatus
from neuromancers_network.meetings.search import search_meetings
from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.taxonomy.models import Language
from neuromancers_network.taxonomy.selectors import meeting_amount_query
from neuromancers_network.taxonomy.selectors import meeting_country_query
from neuromancers_network.taxonomy.selectors import meeting_language_query
from neuromancers_network.taxonomy.selectors import meeting_tag_query
from neuromancers_network.taxonomy.tests.factories import AllowedTagFactory
from neuromancers_network.taxonomy.tests.factories import CountryFactory
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

HTTP_OK = 200
SESSION_DURATION = 30
TIER_PRICE = Decimal("40.00")


@pytest.fixture
def languages():
    return [
        Language.objects.create(name="English", name_local="English", code="en"),
        Language.objects.create(name="German", name_local="Deutsch", code="de"),
    ]


class TestSearchMeetings:
    def test_by_language(self, languages):
        en, de = languages
        english = create_meeting(peer=UserFactory(), title="English", languages=[en])
        create_meeting(peer=UserFactory(), title="German", languages=[de])

        results = search_meetings(languages=[en])
        assert list(results) == [english]

    def test_by_tag_is_case_insensitive(self):
        tagged = create_meeting(
            peer=UserFactory(),
            title="Anxiety",
            tags=["Anxiety & Trauma"],
        )
        create_meeting(peer=UserFactory(), title="Grief", tags=["Grief"])

        results = search_meetings(tags=["anxiety & trauma"])
        assert list(results) == [tagged]

    def test_by_language_and_tag_uses_faceted_and(self, languages):
        en, _ = languages
        matching = create_meeting(
            peer=UserFactory(),
            title="Match",
            languages=[en],
            tags=["anxiety"],
        )
        create_meeting(
            peer=UserFactory(),
            title="Right tag wrong lang",
            tags=["anxiety"],
        )
        create_meeting(peer=UserFactory(), title="Right lang wrong tag", languages=[en])

        results = search_meetings(languages=[en], tags=["anxiety"])
        assert list(results) == [matching]

    def test_excludes_non_published(self, languages):
        en, _ = languages
        published = create_meeting(
            peer=UserFactory(),
            title="Published",
            languages=[en],
        )
        create_meeting(
            peer=UserFactory(),
            title="Draft",
            languages=[en],
            status=MeetingStatus.DRAFT,
        )
        create_meeting(
            peer=UserFactory(),
            title="Archived",
            languages=[en],
            status=MeetingStatus.ARCHIVED,
        )

        results = search_meetings(languages=[en])
        assert list(results) == [published]

    def test_no_filters_returns_all_published(self):
        first = create_meeting(peer=UserFactory(), title="One")
        second = create_meeting(peer=UserFactory(), title="Two")

        results = search_meetings()
        assert set(results) == {first, second}

    def test_does_not_duplicate_multi_match(self, languages):
        en, de = languages
        meeting = create_meeting(peer=UserFactory(), title="Both", languages=[en, de])

        results = search_meetings(languages=[en, de])
        assert list(results) == [meeting]

    def test_inactive_tag_is_excluded(self):
        retired = AllowedTagFactory(name="retired", is_active=False)
        create_meeting(peer=UserFactory(), title="Old", tags=[retired])

        assert list(search_meetings(tags=["retired"])) == []

    def test_by_country(self):
        country = CountryFactory()
        matching = create_meeting(
            peer=UserFactory(),
            title="Local",
            countries=[country],
        )
        create_meeting(peer=UserFactory(), title="Elsewhere")

        results = search_meetings(countries=[country])
        assert list(results) == [matching]


class TestMeetingFilterQueries:
    def test_language_query(self, languages):
        en, de = languages
        english = create_meeting(peer=UserFactory(), title="English", languages=[en])
        create_meeting(peer=UserFactory(), title="German", languages=[de])

        params = QueryDict("filter_language=en")
        results = meeting_language_query(Meeting.objects.all(), params, "language")
        assert list(results) == [english]

    def test_country_query(self):
        country = CountryFactory()
        matching = create_meeting(
            peer=UserFactory(),
            title="Local",
            countries=[country],
        )
        create_meeting(peer=UserFactory(), title="Elsewhere")

        params = QueryDict(f"filter_country={country.code}")
        results = meeting_country_query(Meeting.objects.all(), params, "country")
        assert list(results) == [matching]

    def test_tag_query(self):
        matching = create_meeting(peer=UserFactory(), title="Anxiety", tags=["anxiety"])
        create_meeting(peer=UserFactory(), title="Grief", tags=["grief"])

        params = QueryDict("filter_tag=anxiety")
        results = meeting_tag_query(Meeting.objects.all(), params, "tag")
        assert list(results) == [matching]

    def test_amount_query_uses_tier_price(self):
        tiered = create_meeting(peer=UserFactory(), title="Tiered")
        tier = MeetingPriceTier.objects.create(
            meeting=tiered,
            duration_minutes=SESSION_DURATION,
        )
        MeetingPriceOption.objects.create(
            tier=tier,
            amount=TIER_PRICE,
            is_default=True,
        )
        create_meeting(peer=UserFactory(), title="Cheap")  # flat price of 25

        params = QueryDict("filter_amount_min=30")
        results = meeting_amount_query(Meeting.objects.all(), params, "amount")
        assert set(results) == {tiered}


class TestSearchMeetingsAPI:
    def test_search_endpoint(self, languages, user):
        en, _ = languages
        create_meeting(
            peer=UserFactory(),
            title="English",
            languages=[en],
            tags=["anxiety"],
        )
        create_meeting(peer=UserFactory(), title="German", languages=[])

        client = Client()
        client.force_login(user)
        response = client.get("/api/meetings/search/?languages=en,de&tags=anxiety")

        assert response.status_code == HTTP_OK
        payload = response.json()
        assert [entry["title"] for entry in payload] == ["English"]
        assert payload[0]["languages"] == ["en"]
        assert payload[0]["tags"] == ["anxiety"]
