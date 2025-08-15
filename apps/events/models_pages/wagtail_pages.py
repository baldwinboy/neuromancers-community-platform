import heapq

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel, PanelPlaceholder
from wagtail.contrib.routable_page.models import RoutablePage, route
from wagtail.models import Page

from apps.events.forms import GroupSessionForm, PeerSessionForm
from apps.events.models_sessions.group import GroupSession
from apps.events.models_sessions.peer import PeerSession


class SessionDetailPage(Page):
    session_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=models.Q(
            app_label="events", model__in=["peersession", "groupsession"]
        ),
        verbose_name=_("Session type"),
    )
    session_object_id = models.UUIDField()
    session = GenericForeignKey("session_content_type", "session_object_id")

    parent_page_types = ["events.SessionsIndexPage"]
    subpage_types = []  # No child pages under SessionDetailPage

    content_panels = Page.content_panels + [
        FieldPanel("session_content_type"),
        FieldPanel("session_object_id"),
    ]

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
        if self.session and not self.slug:
            model_name = self.session.__class__.__name__.lower()
            if model_name == "peersession":
                prefix = "peer"
            elif model_name == "groupsession":
                prefix = "group"
            else:
                prefix = "session"

            self.slug = f"{prefix}-{self.session.pk}"
        super().save(*args, **kwargs)

    @property
    def is_session_published(self):
        return getattr(self.session, "is_published", False)


class SessionsIndexPage(RoutablePage):
    max_count = 1

    parent_page_types = ["core.HomePage"]
    subpage_types = ["events.SessionDetailPage"]

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
    def choose_session_type(self, request):
        return render(
            request,
            "events/choose_session_type.html",
            {
                "page": self,
            },
        )

    @route(r"^create/peer/$")
    def create_peer_sesion(self, request):
        if request.method == "POST":
            form = PeerSessionForm(request.POST)
            if form.is_valid():
                return self._create_session_page(form.cleaned_data, "peer")
        else:
            form = PeerSessionForm()
        return render(
            request,
            "events/create_session.html",
            {
                "page": self,
                "form": form,
                "session_type": "Peer",
            },
        )

    @route(r"^create/group/$")
    def create_group_sesion(self, request):
        if request.method == "POST":
            form = GroupSessionForm(request.POST)
            if form.is_valid():
                return self._create_session_page(form.cleaned_data, "group")
        else:
            form = GroupSessionForm()
        return render(
            request,
            "events/create_session.html",
            {
                "page": self,
                "form": form,
                "session_type": "Group",
            },
        )

    @route(r"^create/$")
    def create_session(self, request):
        if request.method == "POST":
            form = PeerSessionForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect(self.url)  # Redirect to index page
        else:
            form = PeerSessionForm()

        return render(
            request,
            "events/create_session.html",
            {
                "page": self,  # so template has access to Wagtail page context
                "form": form,
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

    def _create_session_page(form_data, session_type: str, parent_page=None):
        """
        Create an SessionDetailPage for a given PeerSession or GroupSession instance.
        Only publish it if the session is considered live (e.g. is_published=True).
        """
        if session_type == "group":
            session_model = GroupSession
        elif session_type == "peer":
            session_model = PeerSession
        else:
            raise ValueError(f"Unknown event type: {session_type}")

        # Create the event instance
        session_instance = session_model.objects.create(**form_data)

        # Get or infer parent
        if parent_page is None:
            parent_page = SessionsIndexPage.objects.first()
            if not parent_page:
                raise Exception(
                    "No SessionsIndexPage exists to add the event page under."
                )

        # Build content type for GenericForeignKey
        session_content_type = ContentType.objects.get_for_model(
            session_instance.__class__
        )

        # Create slug from UUID
        model_name = session_instance.__class__.__name__.lower()
        if model_name == "peersession":
            prefix = "peer"
        elif model_name == "groupsession":
            prefix = "group"
        else:
            prefix = "session"
        slug = f"{prefix}-{session_instance.id}"

        # Create the page
        session_page = SessionDetailPage(
            title=session_instance.title,
            slug=slug,
            session_content_type=session_content_type,
            session_object_id=session_instance.id,
        )

        # Add the page as a child of the index page
        parent_page.add_child(instance=session_page)

        # Save revision
        revision = session_page.save_revision()

        # Only publish the page if the linked event is published
        if getattr(session_page, "is_published", True):
            revision.publish()

        return session_page
