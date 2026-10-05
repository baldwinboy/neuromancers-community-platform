from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.snippets.views.snippets import SnippetViewSet

from neuromancers_network.core.bulk_actions import SetActiveBulkAction
from neuromancers_network.taxonomy.models import AllowedTag
from neuromancers_network.taxonomy.models import Country
from neuromancers_network.taxonomy.models import Language
from neuromancers_network.taxonomy.models import TagGroup


class TagGroupFilterSet(WagtailFilterSet):
    class Meta:
        model = TagGroup
        fields = ["is_active"]


class AllowedTagFilterSet(WagtailFilterSet):
    class Meta:
        model = AllowedTag
        fields = ["group", "is_active"]


class LanguageFilterSet(WagtailFilterSet):
    class Meta:
        model = Language
        fields = ["is_active"]


class TagGroupViewSet(SnippetViewSet):
    model = TagGroup
    icon = "tag"
    menu_label = _("Tag groups")
    list_display = ["name", "slug", "sort_order", "is_active"]
    search_fields = ["name", "description"]
    filterset_class = TagGroupFilterSet
    list_per_page = 50


class AllowedTagViewSet(SnippetViewSet):
    model = AllowedTag
    icon = "tag"
    menu_label = _("Allowed tags")
    list_display = ["name", "group", "sort_order", "is_active"]
    search_fields = ["name", "description"]
    filterset_class = AllowedTagFilterSet
    list_per_page = 50


class CountryViewSet(SnippetViewSet):
    model = Country
    icon = "site"
    menu_label = _("Countries")
    list_display = ["name", "code", "sort_order"]
    search_fields = ["name", "code"]
    list_per_page = 50


class LanguageViewSet(SnippetViewSet):
    model = Language
    icon = "globe"
    menu_label = _("Languages")
    list_display = ["name", "code", "sort_order", "is_active"]
    search_fields = ["name", "name_local", "code"]
    filterset_class = LanguageFilterSet
    list_per_page = 50


class ActivateBulkAction(SetActiveBulkAction):
    models = [TagGroup, AllowedTag, Language]
    display_name = _("Activate")
    action_type = "activate"
    aria_label = _("Activate selected items")
    active = True
    icon = "check"
    confirm_message = _("Are you sure you want to activate these items?")
    action_button_text = _("Yes, activate")
    no_action_button_text = _("No, don't activate")


class DeactivateBulkAction(SetActiveBulkAction):
    models = [TagGroup, AllowedTag, Language]
    display_name = _("Deactivate")
    action_type = "deactivate"
    aria_label = _("Deactivate selected items")
    active = False
    icon = "no"
    confirm_message = _("Are you sure you want to deactivate these items?")
    action_button_text = _("Yes, deactivate")
    no_action_button_text = _("No, don't deactivate")


hooks.register("register_bulk_action", ActivateBulkAction)
hooks.register("register_bulk_action", DeactivateBulkAction)
