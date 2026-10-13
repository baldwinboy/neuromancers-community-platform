"""Moderation admin viewsets (Operations submenu)."""

from __future__ import annotations

import contextlib

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.panels import FieldPanel
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.snippets.views.snippets import SnippetViewSetGroup

from neuromancers_network.core.bulk_actions import ConfirmBulkAction
from neuromancers_network.core.views.viewset import HiddenFromSnippetIndexMixin
from neuromancers_network.inbox.events import emit
from neuromancers_network.moderation.models import AccountDeletionRequest
from neuromancers_network.moderation.models import EmailBan
from neuromancers_network.moderation.models import IPBan
from neuromancers_network.moderation.models import SupportStatus
from neuromancers_network.moderation.models import SupportTicket
from neuromancers_network.moderation.models import UserBlock
from neuromancers_network.moderation.services import purge_account


class AccountDeletionFilterSet(WagtailFilterSet):
    class Meta:
        model = AccountDeletionRequest
        fields = ["status"]


class AccountDeletionRequestViewSet(HiddenFromSnippetIndexMixin, SnippetViewSet):
    model = AccountDeletionRequest
    icon = "warning"
    menu_label = _("Deletion requests")
    menu_name = "deletion_requests"
    list_display = [
        "user",
        "status",
        "scheduled_for",
        "completed_at",
        "created_at",
    ]
    search_fields = ["user__username", "user__name", "reason"]
    filterset_class = AccountDeletionFilterSet
    panels = [
        FieldPanel("user"),
        FieldPanel("reason"),
        FieldPanel("status"),
        FieldPanel("scheduled_for"),
    ]
    list_per_page = 50


class PurgeAccountsBulkAction(ConfirmBulkAction):
    models = [AccountDeletionRequest]
    display_name = _("Purge now")
    action_type = "purge"
    aria_label = _("Purge selected accounts now")
    icon = "bin"
    confirm_message = _(
        "Purge the selected accounts now? This anonymises them immediately "
        "and cannot be undone.",
    )
    action_button_text = _("Yes, purge")
    no_action_button_text = _("No, go back")

    @classmethod
    def execute_action(cls, objects, **kwargs):
        purged = 0
        for deletion in objects:
            purge_account(deletion.user)
            purged += 1
        return purged, 0


class UserBlockViewSet(HiddenFromSnippetIndexMixin, SnippetViewSet):
    model = UserBlock
    icon = "no"
    menu_label = _("Member blocks")
    menu_name = "member_blocks"
    menu_order = 2
    list_display = ["blocker", "blocked", "created_at"]
    search_fields = ["blocker__username", "blocked__username"]
    panels = [
        FieldPanel("blocker"),
        FieldPanel("blocked"),
        FieldPanel("reason"),
    ]
    list_per_page = 50


class EmailBanViewSet(HiddenFromSnippetIndexMixin, SnippetViewSet):
    model = EmailBan
    icon = "mail"
    menu_label = _("Email bans")
    menu_name = "email_bans"
    menu_order = 3
    list_display = ["value", "is_domain", "is_active", "created_at"]
    search_fields = ["value", "reason"]
    panels = [
        FieldPanel("value"),
        FieldPanel("is_domain"),
        FieldPanel("is_active"),
        FieldPanel("reason"),
    ]
    list_per_page = 50


class IPBanViewSet(HiddenFromSnippetIndexMixin, SnippetViewSet):
    model = IPBan
    icon = "site"
    menu_label = _("IP bans")
    menu_name = "ip_bans"
    menu_order = 4
    list_display = ["ip_address", "expires_at", "created_at"]
    search_fields = ["ip_address", "reason"]
    panels = [
        FieldPanel("ip_address"),
        FieldPanel("expires_at"),
        FieldPanel("reason"),
    ]
    list_per_page = 50


class SupportTicketFilterSet(WagtailFilterSet):
    class Meta:
        model = SupportTicket
        fields = ["kind", "status"]


class SupportTicketViewSet(HiddenFromSnippetIndexMixin, SnippetViewSet):
    model = SupportTicket
    icon = "help"
    menu_label = _("Support tickets")
    menu_name = "support_tickets"
    menu_order = 5
    list_display = ["kind", "reporter", "status", "assigned_to", "created_at"]
    search_fields = ["message", "reporter__username", "reporter__name"]
    filterset_class = SupportTicketFilterSet
    panels = [
        FieldPanel("kind"),
        FieldPanel("reporter"),
        FieldPanel("subject_user"),
        FieldPanel("subject_url"),
        FieldPanel("message"),
        FieldPanel("status"),
        FieldPanel("assigned_to"),
        FieldPanel("response"),
    ]
    list_per_page = 50


def _resolve_tickets(objects, *, status, actor=None, response=""):
    resolved = 0
    for ticket in objects:
        if ticket.status == status:
            continue
        ticket.status = status
        ticket.resolved_at = timezone.now()
        ticket.assigned_to = actor
        if response:
            ticket.response = response
        ticket.save(
            update_fields=[
                "status",
                "resolved_at",
                "assigned_to",
                "response",
                "updated_at",
            ],
        )
        with contextlib.suppress(Exception):
            emit(
                "report_resolved",
                payload={
                    "actor_user_id": getattr(actor, "pk", None),
                    "recipient_user_ids": (
                        [ticket.reporter_id] if ticket.reporter_id else []
                    ),
                    "object_type": "supportticket",
                    "object_id": ticket.pk,
                    "meta": {"ticket_id": ticket.pk, "status": status},
                },
                event_ref=f"supportticket.{ticket.pk}.{status}",
            )
        resolved += 1
    return resolved, 0


class ResolveSupportTicketsBulkAction(ConfirmBulkAction):
    models = [SupportTicket]
    display_name = _("Resolve")
    action_type = "resolve"
    aria_label = _("Resolve selected support tickets")
    icon = "check"
    confirm_message = _("Mark the selected support tickets as resolved?")
    action_button_text = _("Yes, resolve")
    no_action_button_text = _("No, go back")

    def get_execution_context(self):
        return {"actor": self.request.user}

    @classmethod
    def execute_action(cls, objects, *, actor=None, **kwargs):
        return _resolve_tickets(objects, status=SupportStatus.RESOLVED, actor=actor)


class RejectSupportTicketsBulkAction(ConfirmBulkAction):
    models = [SupportTicket]
    display_name = _("Reject")
    action_type = "reject"
    aria_label = _("Reject selected support tickets")
    icon = "no"
    confirm_message = _("Reject the selected support tickets?")
    action_button_text = _("Yes, reject")
    no_action_button_text = _("No, go back")

    def get_execution_context(self):
        return {"actor": self.request.user}

    @classmethod
    def execute_action(cls, objects, *, actor=None, **kwargs):
        return _resolve_tickets(objects, status=SupportStatus.REJECTED, actor=actor)


class ModerationOperationsViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Moderation")
    menu_name = "operations_moderation"
    menu_icon = "warning"
    menu_order = 5
    items = (
        AccountDeletionRequestViewSet,
        UserBlockViewSet,
        EmailBanViewSet,
        IPBanViewSet,
        SupportTicketViewSet,
    )
    add_to_admin_menu = False


for action_class in (
    PurgeAccountsBulkAction,
    ResolveSupportTicketsBulkAction,
    RejectSupportTicketsBulkAction,
):
    hooks.register("register_bulk_action", action_class)
