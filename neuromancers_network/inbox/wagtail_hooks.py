from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import ObjectList
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.snippets.views.snippets import SnippetViewSet

from neuromancers_network.core.views.viewset import HiddenFromSnippetIndexMixin
from neuromancers_network.inbox.forms import NotificationPreferenceAdminForm
from neuromancers_network.inbox.models import NotificationPreference
from neuromancers_network.inbox.models.daisie_bridge import DaisieBridgeSubscriber


class NotificationPreferenceViewSet(ModelViewSet):
    model = NotificationPreference
    icon = "mail"
    menu_label = _("Notification preferences")
    menu_name = "notification_preferences"
    menu_order = 4
    list_display = ["user", "disabled_event_types_display", "updated_at"]
    search_fields = ["user__username", "user__name"]
    edit_handler = ObjectList(
        [FieldPanel("user"), FieldPanel("disabled_event_types")],
        base_form_class=NotificationPreferenceAdminForm,
    )
    list_per_page = 50


class DaisieBridgeSubscriberViewSet(HiddenFromSnippetIndexMixin, SnippetViewSet):
    model = DaisieBridgeSubscriber
    icon = "mail"
    menu_label = _("Email notifications")
    menu_name = "email_notifications"
    menu_hook = "register_email_submenu"
    list_display = ["label", "event_type", "is_active"]
    search_fields = ["label", "event_type"]
    panels = [
        FieldPanel("label"),
        FieldPanel("event_type"),
        FieldPanel("is_active"),
    ]
    list_per_page = 50


@hooks.register("register_admin_viewset")
def register_bridge_subscriber_viewset():
    return DaisieBridgeSubscriberViewSet()
