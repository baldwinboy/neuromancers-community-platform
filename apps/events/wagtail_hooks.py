from guardian.admin import GuardedModelAdmin
from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register

from .models import GroupSession, PeerSession


class PeerSessionAdmin(ModelAdmin, GuardedModelAdmin):
    model = PeerSession
    menu_icon = "radio-empty"
    list_display = ("title", "host")
    list_filter = ("host",)
    search_fields = ("title", "host")


class GroupSessionAdmin(ModelAdmin, GuardedModelAdmin):
    model = GroupSession
    menu_icon = "radio-full"
    list_display = ("title", "host")
    list_filter = ("host",)
    search_fields = ("title", "host")


class SessionsGroup(ModelAdminGroup):
    menu_label = "Sessions"
    menu_icon = "calendar-alt"
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (PeerSessionAdmin, GroupSessionAdmin)


modeladmin_register(SessionsGroup)
