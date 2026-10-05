from django.utils.translation import gettext_lazy as _
from wagtail.admin.viewsets.model import ModelViewSet

from neuromancers_network.inbox.models import NotificationPreference


class NotificationPreferenceViewSet(ModelViewSet):
    model = NotificationPreference
    icon = "mail"
    menu_label = _("Notification preferences")
    menu_name = "notification_preferences"
    menu_order = 6
    list_display = ["user", "disabled_event_types", "updated_at"]
    search_fields = ["user__username", "user__name"]
    form_fields = ["user", "disabled_event_types"]
    list_per_page = 50
