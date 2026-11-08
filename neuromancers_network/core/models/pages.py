from typing import TYPE_CHECKING

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.http import Http404
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel
from wagtail.search import index
from wagtail_daisIE.detail_pages.models import GeneratedPagesIndexPage
from wagtail_daisIE.detail_pages.models import GeneratedPagesRouteMixin
from wagtail_daisIE.detail_pages.models import ModelDetailPage
from wagtail_daisIE.detail_pages.models import ModelDetailTemplate
from wagtail_daisIE.pages import StyledPageMixin

from neuromancers_network.core.models.tag import StandardPageTag
from neuromancers_network.core.utils import display_reserved_routes_error
from neuromancers_network.core.utils import is_reserved_route

if TYPE_CHECKING:
    from typing import Any

#: detail_key -> the path parameter the matching context model reads.
_SOURCE_PARAM = {
    "meeting": "meeting_pk",
    "peer_profile": "peer_pk",
    "review": "review_pk",
    # user_profile publishes its own params (username-based); see below.
}


class SourceBoundDetailPage(ModelDetailPage):
    """Resolve only this page's own URL-sourced context model.

    daisIE resolves *every* configured context model from the page's ``pk``/
    ``slug``. Because several URL-sourced models share ``lookup_field: "pk"``,
    that binds unrelated rows (e.g. a Meeting on a peer page). We publish the
    page's source under a model-specific parameter and drop any other
    URL-sourced model that is not explicitly bound.
    """

    template = "core/detail_page.html"

    class Meta:
        abstract = True

    def daisie_source_params(self) -> dict[str, Any]:
        name = _SOURCE_PARAM.get(self.detail_key)
        if name and self.source_object_id is not None:
            return {name: self.source_object_id}
        return {}

    def get_context(self, request, *args, **kwargs):
        from wagtail_daisIE.dynamic.registry import get_context_models  # noqa: PLC0415
        from wagtail_daisIE.dynamic.resolvers import parse_bindings  # noqa: PLC0415

        extra = {
            key: value
            for key, value in self.daisie_source_params().items()
            if value is not None
        }
        request.daisie_path_params = dict(extra)

        context = super().get_context(request, *args, **kwargs)

        models = get_context_models()
        template = self.get_template_page()
        explicit = set(parse_bindings(template))
        keep = {self.detail_key, *explicit}
        for key, config in models.items():
            if config.source_kind == "url" and key not in keep:
                context.pop(key, None)
        config = models.get(self.detail_key)
        if (
            self.source is not None
            and config is not None
            and config.model is not None
            and isinstance(self.source, config.model)
        ):
            context[self.detail_key] = self.source
        return context


class ReservedSlugPage(GeneratedPagesRouteMixin, StyledPageMixin):
    """
    A page that cannot be created with a reserved slug.
    """

    class Meta:
        abstract = True

    def route(self, request, path_components):
        # The generated-index segment is an admin-only container. Reject it
        # before GeneratedPagesRouteMixin can route through it.
        if path_components:
            first = path_components[0]
            for child in self.get_children().specific():
                if isinstance(child, GeneratedPagesIndexPage) and child.slug == first:
                    raise Http404
        return super().route(request, path_components)

    def clean(self):
        super().clean()
        self.clean_slug()

    def clean_slug(self):
        if is_reserved_route((self.slug or "").lower()):
            error_message = display_reserved_routes_error(self.slug)
            if not error_message:
                return
            raise ValidationError(
                error_message,
                code="reserved_slug_not_allowed",
            )


class IndexPage(ReservedSlugPage):
    template = "core/index_page.html"

    class Meta:
        abstract = True


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
        "core.SearchPage",
        "peers.PeerApplicationFormPage",
        "peers.PeerApplicationEditFormPage",
        "meetings.MeetingFormPage",
        "meetings.MeetingEditFormPage",
        "meetings.BookingFormPage",
        "meetings.RefundRequestFormPage",
        "meetings.ReviewFormPage",
        "users.ProfileEditFormPage",
        "moderation.SupportFormPage",
        "core.MeetingDetailTemplate",
        "core.PeerDetailTemplate",
        "core.ReviewDetailTemplate",
        "core.UserProfileDetailTemplate",
        "core.TagDetailTemplate",
        "core.BookingDetailTemplate",
        "core.RefundRequestDetailTemplate",
        "core.BookingGeneratedPagesIndexPage",
        "core.RefundRequestGeneratedPagesIndexPage",
    ]


class StandardPage(ReservedSlugPage):
    template = "core/standard_page.html"
    tags = TaggableManager(
        blank=True,
        through=StandardPageTag,
        to="taxonomy.AllowedTag",
    )
    search_fields = [
        *ReservedSlugPage.search_fields,
        index.SearchField("search_description"),
        index.SearchField("body"),
    ]

    content_panels = [*ReservedSlugPage.content_panels, FieldPanel("tags")]


class SearchPage(ReservedSlugPage):
    template = "core/search_page.html"
    subpage_types: list[str] = []

    def get_context(self, request, *args, **kwargs):
        from neuromancers_network.core.search_service import search_site  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        context.update(
            search_site(
                request.GET.get("query", ""),
                request=request,
                page_number=request.GET.get("page", 1),
            ),
        )
        return context


class ProfileIndexPage(IndexPage):
    """Listing page for member profiles; its slug is reserved as ``u``."""

    template = "core/index_page.html"
    subpage_types = ["core.ProfileGeneratedPagesIndexPage"]
    max_count = 1


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
    subpage_types: list[str] = []

    def get_context(self, request, *args, **kwargs):
        from django.urls import reverse  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        token = getattr(request.user, "calendar_feed_token", None)
        if token is not None and token.is_active:
            context["calendar_feed_url"] = request.build_absolute_uri(
                reverse("calendar_feed", args=[token.token]),
            )
        else:
            context["calendar_feed_url"] = ""
        context["calendar_feed_active"] = bool(context["calendar_feed_url"])
        return context


class SettingsPage(SignedInPage):
    """Retired settings page retained for historical migrations."""

    template = "core/settings_page.html"
    subpage_types: list[str] = []
    is_creatable = False


class UserProfilePage(SourceBoundDetailPage):
    parent_page_types = ["core.ProfileGeneratedPagesIndexPage"]
    subpage_types: list[str] = []

    def daisie_source_params(self):
        username = getattr(self.source, "username", None) or self.slug
        return {
            # consumed by binding
            "user__username": username,
            # consumed by audience rules
            "username": username,
            "user_pk": self.source_object_id,
        }


class MeetingIndexPage(IndexPage):
    subpage_types = ["core.MeetingGeneratedPagesIndexPage"]
    max_count = 1
    template = "core/index_page.html"


class PeerIndexPage(IndexPage):
    subpage_types = ["core.PeerGeneratedPagesIndexPage"]
    max_count = 1
    template = "core/index_page.html"


class ReviewIndexPage(IndexPage):
    subpage_types = ["core.ReviewGeneratedPagesIndexPage"]
    max_count = 1
    template = "core/index_page.html"


class MeetingGeneratedPagesIndexPage(GeneratedPagesIndexPage):
    parent_page_types = ["core.MeetingIndexPage"]
    subpage_types = ["core.MeetingDetailPage"]


class PeerGeneratedPagesIndexPage(GeneratedPagesIndexPage):
    parent_page_types = ["core.PeerIndexPage"]
    subpage_types = ["core.PeerProfileDetailPage"]


class ReviewGeneratedPagesIndexPage(GeneratedPagesIndexPage):
    parent_page_types = ["core.ReviewIndexPage"]
    subpage_types = ["core.ReviewDetailPage"]


class ProfileGeneratedPagesIndexPage(GeneratedPagesIndexPage):
    parent_page_types = ["core.ProfileIndexPage"]
    subpage_types = ["core.UserProfilePage"]


class TagGeneratedPagesIndexPage(GeneratedPagesIndexPage):
    parent_page_types = ["core.TagIndexPage"]
    subpage_types = ["core.TagDetailPage"]


class BookingGeneratedPagesIndexPage(GeneratedPagesIndexPage):
    parent_page_types = ["core.HomePage"]
    subpage_types = ["core.BookingDetailPage"]


class RefundRequestGeneratedPagesIndexPage(GeneratedPagesIndexPage):
    parent_page_types = ["core.HomePage"]
    subpage_types = ["core.RefundRequestDetailPage"]


class MeetingDetailTemplate(ModelDetailTemplate):
    """Shared (non-navigable) content and design for meeting pages."""

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []


class PeerDetailTemplate(ModelDetailTemplate):
    """Shared (non-navigable) content and design for care-provider pages."""

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []


class ReviewDetailTemplate(ModelDetailTemplate):
    """Shared (non-navigable) content and design for review pages."""

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []


class UserProfileDetailTemplate(ModelDetailTemplate):
    """Shared (non-navigable) content and design for member-profile pages."""

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []


class TagDetailTemplate(ModelDetailTemplate):
    """Shared (non-navigable) content and design for tag pages."""

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []


class BookingDetailTemplate(ModelDetailTemplate):
    """Shared (non-navigable) content and design for booking pages."""

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []


class RefundRequestDetailTemplate(ModelDetailTemplate):
    """Shared (non-navigable) content and design for refund pages."""

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []


class MeetingDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.MeetingGeneratedPagesIndexPage"]
    subpage_types: list[str] = []
    template = "core/detail_page.html"

    def get_context(self, request, *args, **kwargs):
        from neuromancers_network.meetings.forms_pages import BookingFormPage  # noqa: PLC0415
        from neuromancers_network.meetings.models import MeetingsBookmark  # noqa: PLC0415
        from neuromancers_network.meetings.selectors import review_stats  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        context["is_bookmarked"] = False
        context["booking_url"] = ""
        if self.source is not None:
            context["review_stats"] = review_stats(
                self.source.peer,
                viewer=getattr(request, "user", None),
            )
            booking_page = BookingFormPage.objects.live().first()
            if booking_page is not None:
                url = booking_page.get_url(request)
                if url:
                    context["booking_url"] = f"{url}?meeting={self.source.pk}"
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                context["is_bookmarked"] = MeetingsBookmark.objects.filter(
                    user=user,
                    meetings=self.source,
                ).exists()
        return context


class PeerProfileDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.PeerGeneratedPagesIndexPage"]
    subpage_types: list[str] = []
    template = "core/detail_page.html"

    def get_context(self, request, *args, **kwargs):
        from neuromancers_network.meetings.selectors import review_stats  # noqa: PLC0415
        from neuromancers_network.peers.models import PeersBookmark  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        context["is_bookmarked"] = False
        if self.source is not None:
            context["review_stats"] = review_stats(
                self.source.user,
                viewer=getattr(request, "user", None),
            )
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                context["is_bookmarked"] = PeersBookmark.objects.filter(
                    user=user,
                    peers=self.source,
                ).exists()
        return context

    def daisie_source_params(self):
        params = super().daisie_source_params()  # peer_pk
        user = getattr(self.source, "user", None)
        if user is not None:
            params.update({"user_pk": user.pk, "username": user.username})
        return params


class ReviewDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.ReviewGeneratedPagesIndexPage"]
    subpage_types: list[str] = []
    template = "core/detail_page.html"


class BookingDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.BookingGeneratedPagesIndexPage"]
    subpage_types: list[str] = []
    template = "core/detail_page.html"


class RefundRequestDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.RefundRequestGeneratedPagesIndexPage"]
    subpage_types: list[str] = []
    template = "core/detail_page.html"


class TagIndexPage(IndexPage):
    subpage_types = ["core.TagGeneratedPagesIndexPage"]
    max_count = 1
    template = "core/index_page.html"


class TagDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.TagGeneratedPagesIndexPage"]
    subpage_types: list[str] = []
    template = "core/detail_page.html"

    def get_context(self, request, *args, **kwargs):
        from neuromancers_network.core.selectors import pages_tagged_with  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        context["tagged_pages"] = pages_tagged_with(self.source)
        return context
