from typing import TYPE_CHECKING

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel
from wagtail.search import index
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
        design = self.get_design_source()
        explicit = set(parse_bindings(self)) | set(parse_bindings(design))
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


class ReservedSlugPage(StyledPageMixin):
    """
    A page that cannot be created with a reserved slug.
    """

    class Meta:
        abstract = True

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
        "core.SettingsPage",
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
        "core.BookingDetailTemplate",
        "core.RefundRequestDetailTemplate",
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
    subpage_types: list[str] = []


class SettingsPage(SignedInPage):
    template = "core/settings_page.html"
    subpage_types: list[str] = []


class UserProfilePage(SourceBoundDetailPage):
    parent_page_types = ["core.ProfileIndexPage"]
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
    subpage_types = ["core.MeetingDetailPage"]


class PeerIndexPage(IndexPage):
    subpage_types = ["core.PeerProfileDetailPage"]


class ReviewIndexPage(IndexPage):
    subpage_types = ["core.ReviewDetailPage"]


class MeetingDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.MeetingIndexPage"]
    subpage_types: list[str] = []

    def get_context(self, request, *args, **kwargs):
        from neuromancers_network.meetings.selectors import review_stats  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        if self.source is not None:
            context["review_stats"] = review_stats(
                self.source.peer,
                viewer=getattr(request, "user", None),
            )
        return context


class PeerProfileDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.PeerIndexPage"]
    subpage_types: list[str] = []

    def get_context(self, request, *args, **kwargs):
        from neuromancers_network.meetings.selectors import review_stats  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        if self.source is not None:
            context["review_stats"] = review_stats(
                self.source.user,
                viewer=getattr(request, "user", None),
            )
        return context

    def daisie_source_params(self):
        params = super().daisie_source_params()  # peer_pk
        user = getattr(self.source, "user", None)
        if user is not None:
            params.update({"user_pk": user.pk, "username": user.username})
        return params


class ReviewDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.ReviewIndexPage"]
    subpage_types: list[str] = []


class BookingDetailTemplate(ModelDetailTemplate):
    """Shared (non-navigable) design for generated booking pages."""

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []


class RefundRequestDetailTemplate(ModelDetailTemplate):
    """Shared (non-navigable) design for generated refund pages."""

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []


class BookingDetailPage(SourceBoundDetailPage):
    parent_page_types: list[str] = []
    subpage_types: list[str] = []


class RefundRequestDetailPage(SourceBoundDetailPage):
    parent_page_types: list[str] = []
    subpage_types: list[str] = []


class TagIndexPage(IndexPage):
    subpage_types = ["core.TagDetailPage"]


class TagDetailPage(SourceBoundDetailPage):
    parent_page_types = ["core.TagIndexPage"]
    subpage_types: list[str] = []

    def get_context(self, request, *args, **kwargs):
        from neuromancers_network.core.selectors import pages_tagged_with  # noqa: PLC0415

        context = super().get_context(request, *args, **kwargs)
        context["tagged_pages"] = pages_tagged_with(self.source)
        return context
