from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import render
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel, PanelPlaceholder
from wagtail.models import Page

from apps.events.choices import SessionRequestStatusChoices
from apps.events.forms_sessions.group import (
    GroupSessionPublishForm,
    GroupSessionRequestForm,
)
from apps.events.forms_sessions.peer import PeerSessionPublishForm
from apps.events.models_sessions.group import GroupSession, GroupSessionRequest
from apps.events.models_sessions.peer import PeerSession, PeerSessionRequest

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

        # Show the user's own requests regardless of current permissions
        if (
            self.session
            and isinstance(request.user, User)
            and request.user.is_authenticated
            and not request.user.has_perm("change_peersession", self.session)
        ):
            context["user_requests"] = PeerSessionRequest.objects.filter(
                session=self.session,
                attendee=request.user,
            ).order_by("-created_at")

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
            attendee_approved = self.session.attendee_approved(request.user)
            context["attendee_approved"] = attendee_approved

            # Pass the pending request for withdraw/edit actions
            if not attendee_approved:
                pending_request = self.session.get_pending_request(request.user)
                if pending_request:
                    context["pending_request"] = pending_request

            if attendee_approved:
                # Get the approved request for this attendee
                try:
                    attendee_request = PeerSessionRequest.objects.get(
                        session=self.session,
                        attendee=request.user,
                        status=SessionRequestStatusChoices.APPROVED,
                    )
                    # Meeting link from PeerScheduledSession
                    if hasattr(attendee_request, "scheduled_session"):
                        context[
                            "meeting_link"
                        ] = attendee_request.scheduled_session.meeting_link
                    # Payment handling
                    is_paid_session = self.session.price and self.session.price > 0
                    has_paid = bool(attendee_request.stripe_payment_intent_id)
                    host_has_stripe = hasattr(self.session.host, "stripe_account")
                    context["attendee_request"] = attendee_request
                    context["is_paid_session"] = is_paid_session
                    context["has_paid"] = has_paid
                    context["host_has_stripe"] = host_has_stripe
                    context["requires_payment_for_access"] = (
                        is_paid_session
                        and not self.session.access_before_payment
                        and host_has_stripe
                    )
                except PeerSessionRequest.DoesNotExist:
                    pass

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
        session = self.session

        if (
            session
            and request.user
            and request.user.is_authenticated
            and request.user.has_perm("change_groupsession", session)
        ):
            context["form"] = GroupSessionPublishForm(instance=session)

        if (
            session
            and isinstance(request.user, User)
            and request.user.is_authenticated
            and request.user.has_perm("request_join_session", session)
            and not request.user.has_perm("change_groupsession", session)
        ):
            attendee_requested = session.attendee_requested(request.user)

            if not attendee_requested:
                context["form"] = GroupSessionRequestForm(
                    request.user, session, instance=session
                )

            context["attendee_requested"] = attendee_requested
            attendee_approved = session.attendee_approved(request.user)
            context["attendee_approved"] = attendee_approved

            # Pass the pending request for withdraw actions
            if not attendee_approved:
                pending_request = session.get_pending_request(request.user)
                if pending_request:
                    context["pending_request"] = pending_request

            if attendee_approved:
                # Group session meeting link is on the session itself
                context["meeting_link"] = session.meeting_link
                # Payment handling
                is_paid_session = session.price and session.price > 0
                host_has_stripe = hasattr(session.host, "stripe_account")
                try:
                    attendee_request = GroupSessionRequest.objects.get(
                        session=session,
                        attendee=request.user,
                        status=SessionRequestStatusChoices.APPROVED,
                    )
                    has_paid = bool(attendee_request.stripe_payment_intent_id)
                    context["attendee_request"] = attendee_request
                    context["has_paid"] = has_paid
                except GroupSessionRequest.DoesNotExist:
                    has_paid = False
                context["is_paid_session"] = is_paid_session
                context["host_has_stripe"] = host_has_stripe
                context["requires_payment_for_access"] = (
                    is_paid_session
                    and not session.access_before_payment
                    and host_has_stripe
                )

        context["sessions_index"] = self.get_parent().specific
        return context

    def save(self, *args, **kwargs):
        self.slug = f"group-{self.session.pk}"
        super().save(*args, **kwargs)

    def serve(self, request, *args, **kwargs):
        session = self.session
        # Show error when there is no associated session
        if not session:
            return render(request, "404.html", status=404)
        # Hide from non-owners when the session is not published
        if not (
            session.is_published
            or request.user.has_perm("change_groupsession", session)
        ):
            return render(request, "404.html", status=404)

        # Allow owners to toggle published state
        if (
            request.user.is_authenticated
            and request.user.has_perm("change_groupsession", session)
            and request.method == "POST"
        ):
            form = GroupSessionPublishForm(request.POST, instance=session)
            if form.is_valid():
                form.save()

        attendee_requested = False

        if isinstance(request.user, User):
            attendee_requested = session.attendee_requested(request.user)

        # Allow users to join group session
        if (
            request.user.is_authenticated
            and request.user.has_perm("request_join_session", session)
            and not request.user.has_perm("change_groupsession", session)
            and not attendee_requested
            and request.method == "POST"
        ):
            form = GroupSessionRequestForm(request.user, session, request.POST)
            if form.is_valid():
                form.save()

        return super().serve(request, *args, **kwargs)
