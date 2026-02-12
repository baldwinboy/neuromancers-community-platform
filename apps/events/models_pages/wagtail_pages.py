import heapq
import uuid

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from wagtail.admin.panels import PanelPlaceholder
from wagtail.contrib.routable_page.models import RoutablePage, route
from wagtail.fields import StreamField

from apps.events.blocks import PeerFeedBlock, SessionFeedBlock
from apps.events.decorators import (
    parse_uuid_param,
    stripe_account_required,
    with_route_name,
)
from apps.events.forms import (
    GroupSessionForm,
    PeerSessionAvailabilityForm,
    PeerSessionForm,
    PeerSessionRequestForm,
)
from apps.events.models_pages.wagtail_detail_pages import (
    GroupSessionDetailPage,
    PeerSessionDetailPage,
)
from apps.events.models_sessions.group import GroupSession
from apps.events.models_sessions.peer import PeerSession, PeerSessionAvailability

User = get_user_model()

SESSION_TYPE_MAP = {
    "peer": {
        "ModelCls": PeerSession,
        "ModelFormCls": PeerSessionForm,
        "PageModelCls": PeerSessionDetailPage,
        "add_perm": "events.add_peersession",
        "change_perm": "change_peersession",
    },
    "group": {
        "ModelCls": GroupSession,
        "ModelFormCls": GroupSessionForm,
        "PageModelCls": GroupSessionDetailPage,
        "add_perm": "events.add_groupsession",
        "change_perm": "change_groupsession",
    },
}


class SessionsIndexPage(RoutablePage):
    content = StreamField(
        [
            ("session_feed", SessionFeedBlock()),
            ("peer_feed", PeerFeedBlock()),
        ],
        use_json_field=True,
        null=True,
        blank=True,
    )

    max_count = 1

    parent_page_types = ["core.HomePage"]
    subpage_types = ["events.PeerSessionDetailPage", "events.GroupSessionDetailPage"]

    # Optional Wagtail fields (e.g. intro text, image, etc.) can go here.
    content_panels = RoutablePage.content_panels + ["content"]

    promote_panels = [
        PanelPlaceholder(
            "wagtail.admin.panels.MultiFieldPanel",
            [
                [
                    "show_in_menus",
                ],
                _("For site menus"),
            ],
            {},
        ),
    ]

    @route(r"^create/$", name="choose_session_type")
    @with_route_name("choose_session_type")
    @method_decorator(login_required)
    @method_decorator(stripe_account_required)
    def choose_session_type(self, request: HttpRequest):
        if not request.user.has_perm(
            "events.add_peersession"
        ) or not request.user.has_perm("events.add_groupsession"):
            return render(request, "404.html", status=404)

        return render(
            request,
            "events/choose_session_type.html",
            {
                "page": self,
            },
        )

    @route(r"^create/(?P<session_type>[\w-]+)/$", name="create_session")
    @with_route_name("create_session")
    @method_decorator(login_required)
    @method_decorator(stripe_account_required)
    def create_session(self, request, session_type):
        return self._manage_session(request, session_type=session_type)

    @route(
        r"^edit/(?P<session_type>[\w-]+)/(?P<session_id>[0-9a-f-]+)/$",
        name="edit_session",
    )
    @with_route_name("edit_session")
    @parse_uuid_param("session_id")  # apply only where session_id exists
    @method_decorator(login_required)
    @method_decorator(stripe_account_required)
    def edit_session(self, request, session_type, session_id):
        return self._manage_session(
            request, session_type=session_type, session_id=session_id
        )

    @route(r"^availability/(?P<session_id>[0-9a-f-]+)/$", name="manage_availability")
    @with_route_name("manage_availability")
    @parse_uuid_param("session_id")
    @method_decorator(login_required)
    @method_decorator(stripe_account_required)
    def manage_availability(
        self, request: HttpRequest, session_id: uuid.UUID | None = None
    ):
        try:
            session = PeerSession.objects.get(pk=session_id)
        except PeerSession.DoesNotExist:
            return render(request, "404.html", status=404)
        if not request.user.has_perm("manage_availability", session):
            return render(request, "404.html", status=404)

        if request.method == "POST":
            form = PeerSessionAvailabilityForm(request.POST)
            if form.is_valid():
                form.save(session=session)
                return redirect(session.page.full_url)
        else:
            form = PeerSessionAvailabilityForm()

        return render(
            request,
            "events/manage_session_availability.html",
            {"page": self, "form": form, "hosted_session": session},
        )

    @route(
        r"^availability/delete/(?P<availability_id>[0-9a-f-]+)/$",
        name="delete_availability",
    )
    @with_route_name("delete_availability")
    @parse_uuid_param("availability_id")
    @method_decorator(login_required)
    @method_decorator(stripe_account_required)
    def delete_availability(
        self, request: HttpRequest, availability_id: uuid.UUID | None = None
    ):
        try:
            availability = PeerSessionAvailability.objects.get(pk=availability_id)
        except PeerSessionAvailability.DoesNotExist:
            return render(request, "404.html", status=404)

        session = availability.session

        if not request.user.has_perm("manage_availability", session):
            return redirect("events:choose_session_type")

        PeerSessionAvailability.objects.filter(pk=availability_id).delete()
        return redirect("events:manage_availability", session_id=session.id)

    @route(
        r"^request/schedule/(?P<session_id>[0-9a-f-]+)/$",
        name="request_schedule_session",
    )
    @with_route_name("request_schedule_session")
    @parse_uuid_param("session_id")
    @method_decorator(login_required)
    def request_schedule_session(
        self, request: HttpRequest, session_id: uuid.UUID | None = None
    ):
        try:
            session = PeerSession.objects.get(pk=session_id)
        except PeerSession.DoesNotExist:
            return render(request, "404.html", status=404)

        if request.method == "POST":
            form = PeerSessionRequestForm(request.user, session, request.POST)
            if form.is_valid():
                if request.POST.get("_preview", None):
                    instance = form.save(commit=False)
                    serialized = serializers.serialize("json", [instance])
                    request.session["preview_instance"] = serialized
                    return render(
                        request,
                        "events/request_schedule_session_preview.html",
                        {"page": self, "form": form, "session_request": instance},
                    )

            if "preview_instance" in request.session:
                data = request.session.pop("preview_instance", None)
                if data:
                    instance = list(serializers.deserialize("json", data))[0].object
                    # Final tweaks
                    instance.attendee = request.user
                    instance.session = session
                    instance.save()

                    messages.success(request, _("Your request has been submitted!"))
                    return redirect(session.page.full_url)
        else:
            form = PeerSessionRequestForm(request.user, session)

        return render(
            request,
            "events/request_schedule_session.html",
            {
                "page": self,
                "form": form,
                "hosted_session": session,
                "available_slots": session.available_slots,
            },
        )

    def _manage_session(
        self,
        request: HttpRequest,
        session_type: str | None = None,
        session_id: uuid.UUID | None = None,
    ):
        if (
            not session_type
            or session_type not in list(SESSION_TYPE_MAP.keys())
            or not request.user
        ):
            return render(request, "404.html", status=404)

        url_name = request.route_name

        session_type_map = SESSION_TYPE_MAP[session_type]
        ModelFormCls = session_type_map["ModelFormCls"]
        ModelCls = session_type_map["ModelCls"]
        form = ModelFormCls(request.user)
        template_name = "events/create_session.html"
        instance = None

        if url_name == "create_session":
            if session_id or not request.user.has_perm(session_type_map["add_perm"]):
                return render(request, "404.html", status=404)

            if request.method == "POST":
                form = ModelFormCls(request.user, request.POST)
                if form.is_valid():
                    session_page = self._create_session_page(
                        form.cleaned_data, request.user, session_type
                    )
                    if session_page:
                        return redirect(session_page.full_url)
                    else:
                        return render(request, "404.html", status=404)

            context = {
                "page": self,
                "form": form,
                "session_type": _(session_type.capitalize()),
            }

            return render(
                request,
                template_name,
                context,
            )

        if url_name == "edit_session":
            if not session_id:
                return render(request, "404.html", status=404)

            try:
                instance = ModelCls.objects.get(pk=session_id)
            except ModelCls.DoesNotExist:
                return render(request, "404.html", status=404)

            if not request.user.has_perm(session_type_map["change_perm"], instance):
                return render(request, "404.html", status=404)

            template_name = "events/edit_session.html"
            form = ModelFormCls(request.user, instance=instance)

            if request.method == "POST":
                form = ModelFormCls(request.user, request.POST, instance=instance)
                if form.is_valid():
                    form.save()
                    return redirect(instance.page.full_url)

            context = {
                "page": self,
                "form": form,
                "session_type": _(session_type.capitalize()),
                "hosted_session": instance,
            }

            return render(
                request,
                template_name,
                context,
            )

        return render(request, "404.html", status=404)

    def clean(self):
        super().clean()
        if SessionsIndexPage.objects.exclude(pk=self.pk).exists():
            raise ValidationError("Only one EventIndexPage is allowed.")

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update(self.get_sessions(request))
        return context

    def merged_sessions(self, include_peer_sessions=True, include_group_sessions=True):
        iterators = []

        if include_peer_sessions:
            peer_sessions_iter = (
                PeerSession.objects.filter(is_published=True)
                .order_by("updated_at")
                .iterator()
            )
            peer_sessions_decorated = (
                (e.updated_at, "peer", e) for e in peer_sessions_iter
            )
            iterators.append(peer_sessions_decorated)

        if include_group_sessions:
            groups_iter = (
                GroupSession.objects.filter(is_published=True)
                .order_by("starts_at")
                .iterator()
            )
            groups_decorated = ((e.starts_at, "group", e) for e in groups_iter)
            iterators.append(groups_decorated)

        if not iterators:
            return  # empty generator

        for _timestamp, _session_type, session in heapq.merge(*iterators):
            yield session

    def get_sessions(self, request, per_page=9):
        filter_type = request.GET.get("filter")

        include_peer_sessions = filter_type in (None, "peer")
        include_group_sessions = filter_type in (None, "group")

        sessions_generator = self.merged_sessions(
            include_peer_sessions, include_group_sessions
        )

        page_number = request.GET.get("page", 1)
        per_page = 9

        start = (int(page_number) - 1) * per_page
        end = start + per_page
        sessions_page = []

        for i, session in enumerate(sessions_generator):
            if i >= end:
                break
            if i >= start:
                sessions_page.append(session)

        class LazyPaginator:
            num_pages = None
            page = int(page_number)

            def has_previous(self):
                return self.page > 1

            def has_next(self):
                return len(sessions_generator) == per_page

            def previous_page_number(self):
                return self.page - 1

            def next_page_number(self):
                return self.page + 1

        return {
            "sessions": sessions_page,
            "paginator": LazyPaginator(),
            "filter_type": filter_type,
        }

    def _create_session_page(
        self, form_data, user, session_type: str, parent_page=None
    ):
        if (session_type not in list(SESSION_TYPE_MAP.keys())) or not isinstance(
            user, User
        ):
            return None

        session_type_map = SESSION_TYPE_MAP[session_type]
        ModelCls = session_type_map["ModelCls"]
        PageModelCls = session_type_map["PageModelCls"]
        add_perm = session_type_map["add_perm"]

        if not user.has_perm(add_perm):
            return None

        # Create the event instance
        session_instance = ModelCls.objects.create(**form_data)
        session_instance.save()

        # Get or infer parent
        if parent_page is None:
            parent_page = SessionsIndexPage.objects.first()
            if not parent_page:
                raise Exception(
                    "No SessionsIndexPage exists to add the event page under."
                )

        # Create the page
        session_page = PageModelCls(
            title=session_instance.title,
            slug=f"{session_type}-{session_instance.pk}",
            session=session_instance,
        )
        parent_page.add_child(instance=session_page)
        session_page.save_revision().publish()
        session_page.set_url_path(parent_page)

        return session_page
