"""Registration contract for Operations admin viewsets.

These models are registered as snippets so they get native bulk actions, but
must stay hidden from the generic "Snippets" index (they live in their own
Operations submenu).
"""

from __future__ import annotations

from wagtail.snippets.views.snippets import get_snippet_models_for_index_view

from neuromancers_network.inbox.models import DaisieBridgeSubscriber
from neuromancers_network.meetings.models import Meeting
from neuromancers_network.meetings.models import RefundRequest
from neuromancers_network.meetings.models import Review
from neuromancers_network.peers.models import PeerApplication
from neuromancers_network.peers.models import PeerProfile
from neuromancers_network.taxonomy.models import AllowedTag
from neuromancers_network.taxonomy.models import Country
from neuromancers_network.taxonomy.models import Language
from neuromancers_network.taxonomy.models import TagGroup
from neuromancers_network.users.models import UserProfile

HIDDEN_FROM_SNIPPET_INDEX = [
    PeerApplication,
    PeerProfile,
    UserProfile,
    Meeting,
    Review,
    RefundRequest,
    DaisieBridgeSubscriber,
    AllowedTag,
    TagGroup,
    Country,
    Language,
]


def test_hidden_models_are_excluded_from_snippet_index():
    indexed = set(get_snippet_models_for_index_view())

    for model in HIDDEN_FROM_SNIPPET_INDEX:
        assert model not in indexed, model
