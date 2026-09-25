from django.urls import path
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.snippets.views.snippets import SnippetViewSetGroup

from neuromancers_network.core.models import GlossaryTerm
from neuromancers_network.core.models import HelpArticle
from neuromancers_network.core.models import HelpCategory
from neuromancers_network.core.views.email import SendTestEmailView
from neuromancers_network.core.views.stripe import StripeSyncView
from neuromancers_network.core.views.stripe import StripeWebhookView
from neuromancers_network.inbox.wagtail_hooks import NotificationPreferenceViewSet
from neuromancers_network.meetings.wagtail_hooks import BookingViewSet
from neuromancers_network.meetings.wagtail_hooks import MeetingPriceTierViewSet
from neuromancers_network.meetings.wagtail_hooks import MeetingViewSet
from neuromancers_network.meetings.wagtail_hooks import RefundRequestViewSet
from neuromancers_network.meetings.wagtail_hooks import ReviewViewSet
from neuromancers_network.payments.wagtail_hooks import StripeWebhookEndpointViewSet
from neuromancers_network.peers.wagtail_hooks import PeerApplicationViewSet
from neuromancers_network.peers.wagtail_hooks import PeerProfileViewSet
from neuromancers_network.peers.wagtail_hooks import UserProfileViewSet
from neuromancers_network.taxonomy.wagtail_hooks import AllowedTagViewSet
from neuromancers_network.taxonomy.wagtail_hooks import CountryViewSet
from neuromancers_network.taxonomy.wagtail_hooks import LanguageViewSet
from neuromancers_network.taxonomy.wagtail_hooks import TagGroupViewSet

from .utils import prevent_reserved_routes


class OperationsViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Operations")
    menu_name = "operations"
    menu_icon = "cog"
    menu_order = 200
    items = (
        PeerApplicationViewSet,
        PeerProfileViewSet,
        UserProfileViewSet,
        MeetingViewSet,
        BookingViewSet,
        MeetingPriceTierViewSet,
        RefundRequestViewSet,
        ReviewViewSet,
        TagGroupViewSet,
        AllowedTagViewSet,
        CountryViewSet,
        LanguageViewSet,
        NotificationPreferenceViewSet,
        StripeWebhookEndpointViewSet,
    )


register_snippet(OperationsViewSetGroup)


class HelpArticleViewSet(SnippetViewSet):
    model = HelpArticle
    icon = "doc-full"
    menu_label = _("Help articles")
    menu_name = "help_articles"
    menu_order = 1
    list_display = ["title", "category", "kind", "audience", "is_published"]
    search_fields = ["title", "summary"]
    list_per_page = 50


class HelpCategoryViewSet(SnippetViewSet):
    model = HelpCategory
    icon = "folder"
    menu_label = _("Help categories")
    menu_name = "help_categories"
    menu_order = 2
    list_display = ["name", "sort_order", "is_active"]
    search_fields = ["name"]
    list_per_page = 50


class GlossaryTermViewSet(SnippetViewSet):
    model = GlossaryTerm
    icon = "help"
    menu_label = _("Glossary terms")
    menu_name = "glossary_terms"
    menu_order = 3
    list_display = ["term"]
    search_fields = ["term", "definition"]
    list_per_page = 50


class HelpViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Help")
    menu_name = "help"
    menu_icon = "help"
    menu_order = 210
    items = (HelpArticleViewSet, HelpCategoryViewSet, GlossaryTermViewSet)


register_snippet(HelpViewSetGroup)


@hooks.register("register_admin_urls")
def register_stripe_admin_urls():
    return [
        path("stripe/sync/", StripeSyncView.as_view(), name="stripe_sync"),
        path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe_webhook"),
        path("email/test/", SendTestEmailView.as_view(), name="send_test_email"),
    ]


# Prevent pages from being created with reserved routes
@hooks.register("before_create_page")
def prevent_reserved_routes_before_create_page(request, parent_page):
    return prevent_reserved_routes(request, parent_page=parent_page)


# Prevent pages from being edited with reserved routes
@hooks.register("before_edit_page")
def prevent_reserved_routes_before_edit_page(request, page):
    return prevent_reserved_routes(request, page=page)
