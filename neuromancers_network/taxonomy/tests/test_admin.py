import pytest
from wagtail.snippets.models import get_snippet_models

from neuromancers_network.taxonomy.models import AllowedTag
from neuromancers_network.taxonomy.models import Country
from neuromancers_network.taxonomy.models import Language
from neuromancers_network.taxonomy.models import TagGroup
from neuromancers_network.taxonomy.wagtail_hooks import ActivateBulkAction
from neuromancers_network.taxonomy.wagtail_hooks import DeactivateBulkAction

pytestmark = pytest.mark.django_db


class TestBulkActions:
    def test_activate_tag(self):
        group = TagGroup.objects.create(name="Areas of focus")
        tag = AllowedTag.objects.create(
            name="anxiety",
            group=group,
            is_active=False,
        )

        ActivateBulkAction.execute_action([tag], active=True)

        tag.refresh_from_db()
        assert tag.is_active is True

    def test_deactivate_language(self):
        language = Language.objects.create(
            name="English",
            name_local="English",
            code="en",
            is_active=True,
        )

        DeactivateBulkAction.execute_action([language], active=False)

        language.refresh_from_db()
        assert language.is_active is False


class TestViewSets:
    def test_taxonomy_snippets_are_registered(self):
        registered = set(get_snippet_models())
        assert {TagGroup, AllowedTag, Country, Language} <= registered
