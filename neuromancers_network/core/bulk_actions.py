"""Shared Wagtail admin bulk-action bases.

Subclasses declare ``models`` and the usual ``BulkAction`` metadata, then
implement ``execute_action``. The confirmation template is generic.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from wagtail.admin.views.bulk_action import BulkAction


class ConfirmBulkAction(BulkAction):
    """A bulk action that asks for confirmation, then runs ``execute_action``."""

    template_name = "wagtailadmin/bulk_actions/confirmation/confirm_bulk_action.html"
    action_priority = 60
    icon = "check"
    confirm_message = _("Are you sure you want to continue?")
    action_button_text = _("Yes, continue")
    no_action_button_text = _("No, go back")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "action_title": self.display_name,
                "action_icon": self.icon,
                "confirm_message": self.confirm_message,
                "action_button_text": self.action_button_text,
                "no_action_button_text": self.no_action_button_text,
                "action_button_class": "",
            },
        )
        return context

    def get_success_message(self, num_parent_objects, num_child_objects):
        return ngettext(
            "%(num)d item has been updated",
            "%(num)d items have been updated",
            num_parent_objects,
        ) % {"num": num_parent_objects}


class SetActiveBulkAction(ConfirmBulkAction):
    """Set ``is_active`` on the selected objects."""

    active = True

    def get_execution_context(self):
        return {"active": self.active}

    @classmethod
    def execute_action(cls, objects, *, active=True, **kwargs):
        updated = 0
        for obj in objects:
            if obj.is_active != active:
                obj.is_active = active
                obj.save(update_fields=["is_active"])
                updated += 1
        return updated, 0
