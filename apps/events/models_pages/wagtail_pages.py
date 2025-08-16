import heapq

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from guardian.shortcuts import assign_perm
from wagtail.admin.panels import PanelPlaceholder
from wagtail.contrib.routable_page.models import RoutablePage, route
from wagtail.models import Page

from apps.events.forms import GroupSessionForm, PeerSessionForm
from apps.events.models_sessions.group import GroupSession
from apps.events.models_sessions.peer import PeerSession


class PeerSessionDetailPage(Page):
    session = models.ForeignKey(
        PeerSession, on_delete=models.PROTECT, related_name="page"
    )

    parent_page_types = ["events.SessionsIndexPage"]
    subpage_types = []  # No child pages under SessionDetailPage

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

    def save(self, *args, **kwargs):
        self.slug = f"peer-{self.session.pk}"
        super().save(*args, **kwargs)


class GroupSessionDetailPage(Page):
    session = models.ForeignKey(
        GroupSession, on_delete=models.PROTECT, related_name="page"
    )

    parent_page_types = ["events.SessionsIndexPage"]
    subpage_types = []  # No child pages under SessionDetailPage

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

    def save(self, *args, **kwargs):
        self.slug = f"group-{self.session.pk}"
        super().save(*args, **kwargs)


class SessionsIndexPage(RoutablePage):
    max_count = 1

    parent_page_types = ["core.HomePage"]
    subpage_types = ["events.PeerSessionDetailPage", "events.GroupSessionDetailPage"]

    # Optional Wagtail fields (e.g. intro text, image, etc.) can go here.

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

    @route(r"^create/$")
    @method_decorator(login_required)
    def choose_session_type(self, request):
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

    @route(r"^create/peer/$")
    @method_decorator(login_required)
    def create_peer_sesion(self, request):
        if not request.user.has_perm("events.add_peersession"):
            return render(request, "404.html", status=404)
        if request.method == "POST":
            form = PeerSessionForm(request.POST)
            if form.is_valid():
                return self._create_peer_session_page(
                    form.cleaned_data, user=request.user
                )
        else:
            form = PeerSessionForm()
        return render(
            request,
            "events/create_session.html",
            {
                "page": self,
                "form": form,
                "session_type": _("Peer"),
            },
        )

    @route(r"^create/group/$")
    @method_decorator(login_required)
    def create_group_sesion(self, request):
        if not request.user.has_perm("events.add_groupsession"):
            return render(request, "404.html", status=404)
        if request.method == "POST":
            form = GroupSessionForm(request.POST)
            if form.is_valid():
                return self._create_peer_session_page(
                    form.cleaned_data, user=request.user
                )
        else:
            form = GroupSessionForm()
        return render(
            request,
            "events/create_session.html",
            {
                "page": self,
                "form": form,
                "session_type": _("Group"),
            },
        )

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

    def _create_peer_session_page(self, form_data, user, parent_page=None):
        # Create the event instance
        session_instance = PeerSession.objects.create(**form_data, host=user)

        # Assign permissions to user
        for perm in [
            "manage_availability",
            "schedule_session",
            "change_peersession",
            "delete_peersession",
        ]:
            assign_perm(perm, user, session_instance)

        # Create the page
        session_page = PeerSessionDetailPage(
            title=session_instance.title,
            slug=f"peer-{session_instance.pk}",
            session=session_instance,
        )

        # Add the page as a child of the index page
        parent_page.add_child(instance=session_page)

        # Save revision
        revision = session_page.save_revision()

        # Only publish the page if the linked event is published
        if session_page.is_session_published:
            revision.publish()

        return session_page

    def _create_group_session_page(self, form_data, user, parent_page=None):
        # Create the event instance
        session_instance = GroupSession.objects.create(**form_data, host=user)

        # Assign permissions to user
        for perm in ["change_groupsession", "delete_groupsession"]:
            assign_perm(perm, user, session_instance)

        # Create the page
        session_page = GroupSessionDetailPage(
            title=session_instance.title,
            slug=f"group-{session_instance.pk}",
            session=session_instance,
        )

        # Add the page as a child of the index page
        parent_page.add_child(instance=session_page)

        # Save revision
        revision = session_page.save_revision()

        # Only publish the page if the linked event is published
        if session_page.is_session_published:
            revision.publish()

        return session_page
