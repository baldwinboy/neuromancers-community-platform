import pytest
from wagtail.snippets.models import get_snippet_models
from wagtail_daisIE.dynamic.registry import get_context_model

from neuromancers_network.taxonomy.models import AllowedTag
from neuromancers_network.taxonomy.models import Country
from neuromancers_network.taxonomy.models import Language
from neuromancers_network.taxonomy.models import TagGroup
from neuromancers_network.taxonomy.registry import load_countries
from neuromancers_network.taxonomy.registry import load_languages
from neuromancers_network.taxonomy.selectors import install_tag_group_filters
from neuromancers_network.taxonomy.wagtail_hooks import ActivateBulkAction
from neuromancers_network.taxonomy.wagtail_hooks import AllowedTagViewSet
from neuromancers_network.taxonomy.wagtail_hooks import DeactivateBulkAction
from neuromancers_network.taxonomy.wagtail_hooks import TagGroupViewSet

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

    def test_load_countries_is_idempotent(self):
        created, _updated, _skipped = load_countries()

        assert created > 0
        assert Country.objects.filter(code="GB").exists()

        created_again, updated_again, _skipped = load_countries()
        assert created_again == 0
        assert updated_again == created

    def test_load_languages_creates_iso_639_1(self):
        created, _updated, _skipped = load_languages()

        assert created > 0
        assert Language.objects.filter(code="en").exists()


class TestTagGroupFilters:
    def test_tag_group_becomes_a_feed_filter(self):
        TagGroup.objects.create(name="Lived experience")

        install_tag_group_filters()

        filters = get_context_model("meeting").get_filters()
        assert "tag_group_lived-experience" in filters
        assert filters["tag_group_lived-experience"]["label"] == "Lived experience"


class TestViewSets:
    def test_taxonomy_snippets_are_registered(self):
        registered = set(get_snippet_models())
        assert {TagGroup, AllowedTag, Country, Language} <= registered

    def test_reorder_enabled_for_groups_and_tags(self):
        assert TagGroupViewSet().reorder_view_enabled is True
        assert AllowedTagViewSet().reorder_view_enabled is True

    def test_tag_group_slug_is_editable(self):
        form_class = TagGroupViewSet().get_form_class()
        assert "slug" in form_class.base_fields
