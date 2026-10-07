from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel
from wagtail_daisIE.detail_pages.models import ModelDetailPage
from wagtail_daisIE.pages import StyledPageMixin

from neuromancers_network.core.models.tag import StandardPageTag
from neuromancers_network.core.utils import display_reserved_routes_error
from neuromancers_network.core.utils import is_reserved_route


class ReservedSlugPage(StyledPageMixin):
    """
    A page that cannot be created with a reserved slug.
    """

    class Meta:
        abstract = True

    def clean_slug(self):
        if is_reserved_route(self.slug):
            error_message = display_reserved_routes_error(self.slug)
            if not error_message:
                return
            raise ValidationError(
                error_message,
                code="reserved_slug_not_allowed",
            )


class HomePage(ReservedSlugPage):
    template = "core/home_page.html"
    subpage_types = [
        "core.StandardPage",
        "core.TagIndexPage",
        "core.ProfileIndexPage",
        "core.MeetingIndexPage",
        "core.PeerIndexPage",
        "core.ReviewIndexPage",
        "core.DashboardPage",
        "core.SettingsPage",
        "core.SearchPage",
        "peers.PeerApplicationFormPage",
        "meetings.MeetingFormPage",
        "meetings.BookingFormPage",
        "meetings.RefundRequestFormPage",
        "meetings.ReviewFormPage",
        "users.ProfileEditFormPage",
    ]


class StandardPage(ReservedSlugPage):
    template = "core/standard_page.html"
    tags = TaggableManager(
        blank=True,
        through=StandardPageTag,
        to="taxonomy.AllowedTag",
    )

    content_panels = [*ReservedSlugPage.content_panels, FieldPanel("tags")]


class SearchPage(ReservedSlugPage):
    template = "core/search_page.html"
    subpage_types = []

    def get_context(self, request, *args, **kwargs):
        from django.db.models import Q  # noqa: PLC0415

        from neuromancers_network.meetings.search import (  # noqa: PLC0415
            search_meetings,
        )
        from neuromancers_network.peers.search import search_peers  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        query = (request.GET.get("query") or "").strip()
        results = []
        if query:
            meetings = search_meetings().filter(
                Q(title__icontains=query) | Q(description__icontains=query),
            )
            peers = search_peers().filter(
                Q(bio__icontains=query)
                | Q(user__name__icontains=query)
                | Q(user__username__icontains=query),
            )
            results = [*meetings, *peers]
        context["query"] = query
        context["search_results"] = results
        return context


class ProfileIndexPage(ReservedSlugPage):
    """Listing page for member profiles; its slug is reserved as ``u``."""

    template = "core/profile_index_page.html"
    subpage_types = ["core.UserProfilePage"]


class SignedInPage(ReservedSlugPage):
    """Base for pages that require an authenticated member."""

    class Meta:
        abstract = True

    def serve(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return super().serve(request, *args, **kwargs)


class DashboardPage(SignedInPage):
    template = "core/dashboard_page.html"
    subpage_types = []


class SettingsPage(SignedInPage):
    template = "core/settings_page.html"
    subpage_types = []


class UserProfilePage(ModelDetailPage):
    template = "core/user_profile_page.html"
    parent_page_types = ["core.ProfileIndexPage"]
    subpage_types = []


class MeetingIndexPage(ReservedSlugPage):
    template = "core/meeting_index_page.html"
    subpage_types = ["core.MeetingDetailPage"]


class PeerIndexPage(ReservedSlugPage):
    template = "core/peer_index_page.html"
    subpage_types = ["core.PeerProfileDetailPage"]


class ReviewIndexPage(ReservedSlugPage):
    template = "core/review_index_page.html"
    subpage_types = ["core.ReviewDetailPage"]


class MeetingDetailPage(ModelDetailPage):
    template = "core/meeting_detail_page.html"
    parent_page_types = ["core.MeetingIndexPage"]
    subpage_types = []


class PeerProfileDetailPage(ModelDetailPage):
    template = "core/peer_profile_detail_page.html"
    parent_page_types = ["core.PeerIndexPage"]
    subpage_types = []


class ReviewDetailPage(ModelDetailPage):
    template = "core/review_detail_page.html"
    parent_page_types = ["core.ReviewIndexPage"]
    subpage_types = []


class TagIndexPage(ReservedSlugPage):
    template = "core/tag_index_page.html"
    subpage_types = ["core.TagDetailPage"]


class TagDetailPage(ModelDetailPage):
    template = "core/tag_detail_page.html"
    parent_page_types = ["core.TagIndexPage"]
    subpage_types = []

    def get_context(self, request, *args, **kwargs):
        from neuromancers_network.core.selectors import (  # noqa: PLC0415
            pages_tagged_with,
        )

        context = super().get_context(request, *args, **kwargs)
        context["tagged_pages"] = pages_tagged_with(self.source)
        return context
