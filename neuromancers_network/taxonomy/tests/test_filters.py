import pytest
from wagtail_daisIE.dynamic.registry import get_context_model

from neuromancers_network.taxonomy.models import TagGroup
from neuromancers_network.taxonomy.selectors import install_tag_group_filters

pytestmark = pytest.mark.django_db


class TestTagGroupFilters:
    def test_tag_group_becomes_a_feed_filter(self):
        TagGroup.objects.create(name="Lived experience")

        install_tag_group_filters()

        filters = get_context_model("meeting").get_filters()
        assert "tag_group_lived-experience" in filters
        assert filters["tag_group_lived-experience"]["label"] == "Lived experience"
