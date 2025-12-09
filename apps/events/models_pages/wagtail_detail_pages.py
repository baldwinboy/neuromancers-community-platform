from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import render
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel, PanelPlaceholder
from wagtail.models import Page

from apps.events.forms_sessions.group import (
    GroupSessionPublishForm,
    GroupSessionRequestForm,
)
from apps.events.forms_sessions.peer import PeerSessionPublishForm
from apps.events.models_sessions.group import GroupSession
from apps.events.models_sessions.peer import PeerSession

User = get_user_model()


class PeerSessionDetailPage(Page):
    template = "events/view_session.html"

    session = models.OneToOneField(
        PeerSession, on_delete=models.PROTECT, related_name="page"
    )

    parent_page_types = ["events.SessionsIndexPage"]
    subpage_types = []  # No child pages under SessionDetailPage

    content_panels = Page.content_panels + [FieldPanel("session")]

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

    @property
    def session_type(self):
        return "peer"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        if (
            self.session
            and request.user
            and request.user.is_authenticated
            and request.user.has_perm("change_peersession", self.session)
        ):
            context["form"] = PeerSessionPublishForm(instance=self.session)

        if (
            self.session
            and isinstance(request.user, User)
            and request.user.is_authenticated
            and request.user.has_perm("request_session", self.session)
            and not request.user.has_perm("change_peersession", self.session)
        ):
            context["attendee_requested"] = self.session.attendee_requested(
                request.user
            )
            context["attendee_approved"] = self.session.attendee_approved(request.user)

        context["sessions_index"] = self.get_parent().specific
        return context

    def save(self, *args, **kwargs):
        self.slug = f"peer-{self.session.pk}"
        super().save(*args, **kwargs)

    def serve(self, request, *args, **kwargs):
        # Show error when there is no associated session
        if not self.session:
            return render(request, "404.html", status=404)
        # Hide from non-owners when the session is not published
        if not (
            self.session.is_published
            or request.user.has_perm("change_peersession", self.session)
        ):
            return render(request, "404.html", status=404)

        # Allow owners to toggle published state
        if (
            request.user.is_authenticated
            and request.user.has_perm("change_peersession", self.session)
            and request.method == "POST"
        ):
            form = PeerSessionPublishForm(request.POST, instance=self.session)
            if form.is_valid():
                form.save()
        return super().serve(request, *args, **kwargs)


class GroupSessionDetailPage(Page):
    template = "events/view_session.html"

    session = models.OneToOneField(
        GroupSession, on_delete=models.PROTECT, related_name="page"
    )

    parent_page_types = ["events.SessionsIndexPage"]
    subpage_types = []  # No child pages under SessionDetailPage

    content_panels = Page.content_panels + [FieldPanel("session")]

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

    @property
    def session_type(self):
        return "group"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        if (
            self.session
            and request.user
            and request.user.is_authenticated
            and request.user.has_perm("change_groupsession", self.session)
        ):
            context["form"] = GroupSessionPublishForm(instance=self.session)

        if (
            self.session
            and isinstance(request.user, User)
            and request.user.is_authenticated
            and request.user.has_perm("request_join_session", self.session)
            and not request.user.has_perm("change_groupsession", self.session)
        ):
            attendee_requested = self.session.attendee_requested(request.user)

            if not attendee_requested:
                context["form"] = GroupSessionRequestForm(
                    request.user, self.session, instance=self.session
                )

            context["attendee_requested"] = attendee_requested
            context["attendee_approved"] = self.session.attendee_approved(request.user)

        context["sessions_index"] = self.get_parent().specific
        return context

    def save(self, *args, **kwargs):
        self.slug = f"group-{self.session.pk}"
        super().save(*args, **kwargs)

    def serve(self, request, *args, **kwargs):
        # Show error when there is no associated session
        if not self.session:
            return render(request, "404.html", status=404)
        # Hide from non-owners when the session is not published
        if not (
            self.session.is_published
            or request.user.has_perm("change_groupsession", self.session)
        ):
            return render(request, "404.html", status=404)

        # Allow owners to toggle published state
        if (
            request.user.is_authenticated
            and request.user.has_perm("change_groupsession", self.session)
            and request.method == "POST"
        ):
            form = GroupSessionPublishForm(request.POST, instance=self.session)
            if form.is_valid():
                form.save()

        attendee_requested = False

        if isinstance(request.user, User):
            attendee_requested = self.session.attendee_requested(request.user)

        # Allow users to join group session
        if (
            request.user.is_authenticated
            and request.user.has_perm("request_join_session", self.session)
            and not request.user.has_perm("change_groupsession", self.session)
            and not attendee_requested
            and request.method == "POST"
        ):
            form = GroupSessionRequestForm(request.user, self.session, request.POST)
            if form.is_valid():
                form.save()

        return super().serve(request, *args, **kwargs)
