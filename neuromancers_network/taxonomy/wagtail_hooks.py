from django.urls import path
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import TitleFieldPanel
from wagtail.admin.widgets.button import Button
from wagtail.admin.widgets.button import HeaderButton
from wagtail.snippets.views.snippets import CreateView
from wagtail.snippets.views.snippets import EditView
from wagtail.snippets.views.snippets import IndexView
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.snippets.views.snippets import SnippetViewSetGroup

from neuromancers_network.core.bulk_actions import SetActiveBulkAction
from neuromancers_network.taxonomy.models import AllowedTag
from neuromancers_network.taxonomy.models import Country
from neuromancers_network.taxonomy.models import Language
from neuromancers_network.taxonomy.models import TagGroup
from neuromancers_network.taxonomy.views import LoadCountriesView
from neuromancers_network.taxonomy.views import LoadLanguagesView


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


class TagGroupEditView(EditView):
    def get_header_more_buttons(self):
        more_buttons = super().get_header_more_buttons()
        url = reverse("wagtailsnippets_taxonomy_allowedtag:list")
        url = f"{url}?group={self.object.pk}"
        more_buttons.append(
            Button(
                _("Manage tags"),
                url=url,
                icon_name="tag",
                priority=0,
            ),
        )
        return more_buttons


class AllowedTagIndexView(IndexView):
    """Tag listing that keeps the active filter when opening the add view."""

    def get_add_url(self):
        url = super().get_add_url()
        query = self.request.GET.urlencode()
        if url and query:
            return f"{url}?{query}"
        return url


class AllowedTagCreateView(CreateView):
    """Prefill the group when adding a tag from a group-filtered listing."""

    def get_initial_form_instance(self):
        instance = super().get_initial_form_instance()
        if instance is None:
            instance = self.model()
        group_id = self.request.GET.get("group")
        if group_id:
            instance.group_id = group_id
        return instance


class RegistryIndexView(IndexView):
    """Listing with a header button to load entries from the ISO registry."""

    load_registry_url_name = ""

    @cached_property
    def header_buttons(self):
        buttons = list(super().header_buttons)
        if self.load_registry_url_name:
            buttons.append(
                HeaderButton(
                    _("Load all from registry"),
                    url=reverse(self.load_registry_url_name),
                    icon_name="download",
                ),
            )
        return buttons


class CountryIndexView(RegistryIndexView):
    load_registry_url_name = "taxonomy_load_countries"


class LanguageIndexView(RegistryIndexView):
    load_registry_url_name = "taxonomy_load_languages"


class AllowedTagViewSet(SnippetViewSet):
    model = AllowedTag
    icon = "radio-full"
    menu_label = _("Tags")
    list_display = ["name", "group", "sort_order", "is_active"]
    search_fields = ["name", "description"]
    filterset_class = AllowedTagFilterSet
    index_view_class = AllowedTagIndexView
    add_view_class = AllowedTagCreateView
    list_per_page = 50
    panels = [
        TitleFieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("group"),
        FieldPanel("description"),
        FieldPanel("sort_order"),
        FieldPanel("is_active"),
    ]
    add_to_admin_menu = False


class TagGroupViewSet(SnippetViewSet):
    model = TagGroup
    icon = "dots-horizontal"
    menu_label = _("Tag groups")
    list_display = ["name", "slug", "sort_order", "is_active"]
    search_fields = ["name", "description"]
    filterset_class = TagGroupFilterSet
    list_per_page = 50
    edit_view_class = TagGroupEditView
    panels = [
        TitleFieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("sort_order"),
        FieldPanel("is_active"),
    ]


class CountryViewSet(SnippetViewSet):
    model = Country
    icon = "site"
    menu_label = _("Countries")
    index_view_class = CountryIndexView
    list_display = ["name", "code", "sort_order"]
    search_fields = ["name", "code"]
    list_per_page = 50


class LanguageViewSet(SnippetViewSet):
    model = Language
    icon = "globe"
    menu_label = _("Languages")
    index_view_class = LanguageIndexView
    list_display = ["name", "code", "sort_order", "is_active"]
    search_fields = ["name", "name_local", "code"]
    filterset_class = LanguageFilterSet
    list_per_page = 50


class FiltersOperationsViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Filters")
    menu_name = "operations_filters"
    menu_icon = "sliders"
    menu_order = 3
    items = (
        TagGroupViewSet,
        CountryViewSet,
        LanguageViewSet,
    )
    add_to_admin_menu = False


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


@hooks.register("register_admin_viewset")
def register_allowed_tag_viewset():
    return AllowedTagViewSet()


@hooks.register("register_admin_urls")
def register_taxonomy_admin_urls():
    return [
        path(
            "taxonomy/load-countries/",
            LoadCountriesView.as_view(),
            name="taxonomy_load_countries",
        ),
        path(
            "taxonomy/load-languages/",
            LoadLanguagesView.as_view(),
            name="taxonomy_load_languages",
        ),
    ]
