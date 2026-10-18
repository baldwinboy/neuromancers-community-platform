import pytest
from wagtail_daisIE.dynamic.registry import get_context_model

from neuromancers_network.taxonomy.models import TagGroup
from neuromancers_network.taxonomy.selectors import install_tag_group_filters
from neuromancers_network.taxonomy.selectors import tag_choices
from neuromancers_network.taxonomy.tests.factories import AllowedTagFactory
from neuromancers_network.taxonomy.tests.factories import TagGroupFactory

pytestmark = pytest.mark.django_db


class TestTagChoices:
    def test_excludes_tags_in_inactive_groups(self):
        AllowedTagFactory(
            group=TagGroupFactory(is_active=True),
            name="Active",
            slug="active",
        )
        AllowedTagFactory(
            group=TagGroupFactory(is_active=False),
            name="Inactive",
            slug="inactive",
        )

        slugs = [slug for slug, _name in tag_choices()]

        assert "active" in slugs
        assert "inactive" not in slugs


class TestTagGroupFilters:
    def test_tag_group_becomes_a_feed_filter(self):
        TagGroup.objects.create(name="Lived experience")

        install_tag_group_filters()

        filters = get_context_model("meeting").get_filters()
        assert "tag_group_lived-experience" in filters
        assert filters["tag_group_lived-experience"]["label"] == "Lived experience"
