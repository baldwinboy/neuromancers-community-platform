import pytest
from django.test import Client

from neuromancers_network.meetings.tests.factories import create_meeting
from neuromancers_network.peers.search import search_peers
from neuromancers_network.taxonomy.models import Language
from neuromancers_network.taxonomy.tests.factories import AllowedTagFactory
from neuromancers_network.taxonomy.tests.factories import CountryFactory
from neuromancers_network.taxonomy.tests.factories import ensure_tag
from neuromancers_network.users.tests.factories import PeerProfileFactory

pytestmark = pytest.mark.django_db

HTTP_OK = 200


@pytest.fixture
def languages():
    return [
        Language.objects.create(name="English", name_local="English", code="en"),
        Language.objects.create(name="Spanish", name_local="Español", code="es"),
    ]


class TestSearchPeers:
    def test_by_own_language(self, languages):
        en, _ = languages
        peer = PeerProfileFactory(is_approved=True)
        peer.languages.add(en)
        PeerProfileFactory(is_approved=True)

        assert list(search_peers(languages=[en])) == [peer]

    def test_by_own_tag(self):
        peer = PeerProfileFactory(is_approved=True)
        peer.tags.add(ensure_tag("anxiety"))
        PeerProfileFactory(is_approved=True)

        assert list(search_peers(tags=["anxiety"])) == [peer]

    def test_found_via_meeting_language(self, languages):
        en, _ = languages
        meeting_peer = PeerProfileFactory(is_approved=True)
        create_meeting(peer=meeting_peer.user, title="In English", languages=[en])
        PeerProfileFactory(is_approved=True)

        assert list(search_peers(languages=[en])) == [meeting_peer]

    def test_found_via_meeting_tag(self):
        meeting_peer = PeerProfileFactory(is_approved=True)
        create_meeting(peer=meeting_peer.user, title="Anxiety group", tags=["anxiety"])
        PeerProfileFactory(is_approved=True)

        assert list(search_peers(tags=["anxiety"])) == [meeting_peer]

    def test_faceted_and_across_profile_and_meeting(self, languages):
        en, es = languages
        profile_language_meeting_tag = PeerProfileFactory(is_approved=True)
        profile_language_meeting_tag.languages.add(en)
        create_meeting(peer=profile_language_meeting_tag.user, tags=["anxiety"])

        meeting_language_profile_tag = PeerProfileFactory(is_approved=True)
        meeting_language_profile_tag.tags.add(ensure_tag("anxiety"))
        create_meeting(peer=meeting_language_profile_tag.user, languages=[en])

        create_meeting(peer=PeerProfileFactory(is_approved=True).user, languages=[en])
        profile_spanish = PeerProfileFactory(is_approved=True)
        profile_spanish.languages.add(es)
        profile_spanish.tags.add(ensure_tag("anxiety"))

        results = search_peers(languages=[en], tags=["anxiety"])
        assert set(results) == {
            profile_language_meeting_tag,
            meeting_language_profile_tag,
        }

    def test_excludes_unapproved_peers(self, languages):
        en, _ = languages
        approved = PeerProfileFactory(is_approved=True)
        create_meeting(peer=approved.user, languages=[en])
        unapproved = PeerProfileFactory(is_approved=False)
        create_meeting(peer=unapproved.user, languages=[en])

        results = search_peers(languages=[en])
        assert list(results) == [approved]

    def test_excludes_meeting_matches_when_disabled(self, languages):
        en, _ = languages
        own = PeerProfileFactory(is_approved=True)
        own.languages.add(en)
        meeting_only = PeerProfileFactory(is_approved=True)
        create_meeting(peer=meeting_only.user, languages=[en])

        results = search_peers(languages=[en], include_meeting_matches=False)
        assert list(results) == [own]

    def test_no_duplicates_when_profile_and_meetings_match(self, languages):
        en, _ = languages
        peer = PeerProfileFactory(is_approved=True)
        peer.languages.add(en)
        create_meeting(peer=peer.user, title="One", languages=[en])
        create_meeting(peer=peer.user, title="Two", languages=[en])

        assert list(search_peers(languages=[en])) == [peer]

    def test_inactive_tag_is_excluded(self):
        peer = PeerProfileFactory(is_approved=True)
        peer.tags.add(AllowedTagFactory(name="retired", is_active=False))

        assert list(search_peers(tags=["retired"])) == []

    def test_by_country(self):
        country = CountryFactory()
        peer = PeerProfileFactory(is_approved=True)
        peer.countries.add(country)
        PeerProfileFactory(is_approved=True)

        assert list(search_peers(countries=[country])) == [peer]

    def test_found_via_meeting_country(self):
        country = CountryFactory()
        peer = PeerProfileFactory(is_approved=True)
        create_meeting(peer=peer.user, title="Local", countries=[country])
        PeerProfileFactory(is_approved=True)

        assert list(search_peers(countries=[country])) == [peer]


class TestSearchPeersAPI:
    def test_search_endpoint_finds_peer_via_meeting(self, languages, user):
        en, _ = languages
        meeting_peer = PeerProfileFactory(is_approved=True)
        meeting_peer.languages.add(en)
        create_meeting(
            peer=meeting_peer.user,
            title="Anxiety support",
            tags=["anxiety"],
        )
        PeerProfileFactory(is_approved=True)

        client = Client()
        client.force_login(user)
        response = client.get("/api/peers/search/?languages=en&tags=anxiety")

        assert response.status_code == HTTP_OK
        payload = response.json()
        assert [entry["username"] for entry in payload] == [meeting_peer.user.username]
        assert payload[0]["languages"] == ["en"]
        assert payload[0]["tags"] == []
