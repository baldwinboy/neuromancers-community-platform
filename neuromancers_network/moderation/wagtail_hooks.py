"""Moderation admin viewsets (Operations submenu)."""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.panels import FieldPanel
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.snippets.views.snippets import SnippetViewSetGroup

from neuromancers_network.core.bulk_actions import ConfirmBulkAction
from neuromancers_network.core.views.viewset import HiddenFromSnippetIndexMixin
from neuromancers_network.moderation.models import AccountDeletionRequest
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


class ModerationOperationsViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Moderation")
    menu_name = "operations_moderation"
    menu_icon = "warning"
    menu_order = 5
    items = (AccountDeletionRequestViewSet, UserBlockViewSet)
    add_to_admin_menu = False


hooks.register("register_bulk_action", PurgeAccountsBulkAction)
