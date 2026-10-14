from django.urls import path
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.viewsets.base import ViewSetGroup
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.snippets.views.snippets import SnippetViewSetGroup

from neuromancers_network.core.models import GlossaryTerm
from neuromancers_network.core.models import HelpArticle
from neuromancers_network.core.models import HelpCategory
from neuromancers_network.core.panels import HelpGuidePanel
from neuromancers_network.core.views.email import SendTestEmailView
from neuromancers_network.core.views.help import HelpGuideView
from neuromancers_network.core.views.stripe import StripeSyncView
from neuromancers_network.core.views.stripe import StripeWebhookView
from neuromancers_network.inbox.wagtail_hooks import NotificationPreferenceViewSet
from neuromancers_network.meetings.wagtail_hooks import MeetingOperationsViewSetGroup
from neuromancers_network.moderation.wagtail_hooks import (
    ModerationOperationsViewSetGroup,
)
from neuromancers_network.payments.wagtail_hooks import StripeWebhookEndpointViewSet
from neuromancers_network.peers.wagtail_hooks import PeerApplicationViewSet
from neuromancers_network.peers.wagtail_hooks import PeerProfileViewSet
from neuromancers_network.peers.wagtail_hooks import UserProfileViewSet
from neuromancers_network.taxonomy.wagtail_hooks import FiltersOperationsViewSetGroup

from .utils import prevent_reserved_routes


# Change the order of the `Help` menu item
@hooks.register("construct_main_menu")
def reorder_menu_items(request, menu_items):
    for item in menu_items:
        if item.name == "help":
            item.order = 210
            break


class ProfileOperationsViewSetGroup(ViewSetGroup):
    menu_label = _("Profiles")
    menu_name = "operations_profiles"
    menu_icon = "group"
    menu_order = 1
    items = (
        PeerApplicationViewSet,
        PeerProfileViewSet,
        UserProfileViewSet,
        NotificationPreferenceViewSet,
    )
    add_to_admin_menu = False


class ReadOnlyOperationsViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Read-only")
    menu_name = "operations_read_only"
    menu_icon = "lock"
    menu_order = 4
    items = (StripeWebhookEndpointViewSet,)
    add_to_admin_menu = False


class OperationsViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Operations")
    menu_name = "operations"
    menu_icon = "cog"
    menu_order = 200
    items = (
        ProfileOperationsViewSetGroup,
        MeetingOperationsViewSetGroup,
        FiltersOperationsViewSetGroup,
        ReadOnlyOperationsViewSetGroup,
        ModerationOperationsViewSetGroup,
    )


register_snippet(OperationsViewSetGroup)


class HelpCategoryViewSet(SnippetViewSet):
    model = HelpCategory
    icon = "folder"
    menu_label = _("Categories")
    menu_name = "help_categories"
    menu_order = 1
    list_display = ["name", "sort_order", "is_active"]
    search_fields = ["name"]
    list_per_page = 50
    add_to_admin_menu = False


class HelpArticleViewSet(SnippetViewSet):
    model = HelpArticle
    icon = "doc-full"
    menu_label = _("Articles")
    menu_name = "help_articles"
    menu_order = 2
    list_display = ["title", "category", "kind", "audience", "is_published"]
    search_fields = ["title", "summary"]
    list_per_page = 50
    add_to_admin_menu = False


class GlossaryTermViewSet(SnippetViewSet):
    model = GlossaryTerm
    icon = "help"
    menu_label = _("Glossary")
    menu_name = "glossary_terms"
    menu_order = 3
    list_display = ["term"]
    search_fields = ["term", "definition"]
    list_per_page = 50
    add_to_admin_menu = False


class HelpViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Admin Guide")
    menu_name = "admin_help"
    menu_icon = "help"
    menu_hook = "register_help_menu_item"
    items = (HelpCategoryViewSet, HelpArticleViewSet, GlossaryTermViewSet)


register_snippet(HelpViewSetGroup)


@hooks.register("register_admin_urls")
def register_core_admin_urls():
    return [
        path("stripe/sync/", StripeSyncView.as_view(), name="stripe_sync"),
        path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe_webhook"),
        path("email/test/", SendTestEmailView.as_view(), name="send_test_email"),
        path("help/", HelpGuideView.as_view(), name="help_guide"),
    ]


@hooks.register("construct_homepage_panels")
def add_help_guide_panel(request, panels):
    panels.append(HelpGuidePanel())


@hooks.register("before_serve_page")
def hide_inaccessible_detail_pages(page, request, args, kwargs):
    """Return the daisIE 404 for a detail page whose source is not viewable.

    Generated detail pages stay ``live`` after their source is unpublished, a
    plan lapses, or a block is placed (the bridge only ever publishes), so the
    visibility rule is re-applied per request rather than trusted from page
    state. Non-detail pages (no ``source``) are left untouched.
    """
    specific = getattr(page, "specific", page)
    source = getattr(specific, "source", None)
    if source is None:
        return None

    from neuromancers_network.moderation.visibility import (  # noqa: PLC0415
        viewer_can_view_source,
    )

    if viewer_can_view_source(source, getattr(request, "user", None)):
        return None

    from wagtail_daisIE.errors.handlers import render_error_page  # noqa: PLC0415

    return render_error_page(request, 404)


# Prevent pages from being created with reserved routes
@hooks.register("before_create_page")
def prevent_reserved_routes_before_create_page(request, parent_page, page):
    return prevent_reserved_routes(request, parent_page=parent_page)


# Prevent pages from being edited with reserved routes
@hooks.register("before_edit_page")
def prevent_reserved_routes_before_edit_page(request, page):
    return prevent_reserved_routes(request, page=page)
