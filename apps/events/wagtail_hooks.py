from django.dispatch import receiver
from guardian.admin import GuardedModelAdmin
from wagtail.signals import page_published
from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register

from .models import GroupSession, PeerSession, SessionsIndexPage, PeerSessionRequest


@receiver(page_published)
def enforce_sessions_slug(sender, instance, **kwargs):
    if isinstance(instance, SessionsIndexPage) and instance.slug != "sessions":
        instance.slug = "sessions"
        instance.save()
        # Publish only if needed
        if not instance.live:
            instance.save_revision().publish()


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

class PeerSessionRequestAdmin(ModelAdmin, GuardedModelAdmin):
    model = PeerSessionRequest
    menu_icon = "mail"
    list_display = ("session", "attendee", "starts_at", "ends_at")
    list_filter = ("session", "attendee", "starts_at", "ends_at")
    search_fields = ("session", "attendee",)


class SessionsGroup(ModelAdminGroup):
    menu_label = "Sessions"
    menu_icon = "calendar-alt"
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (PeerSessionAdmin, PeerSessionRequestAdmin, GroupSessionAdmin)


modeladmin_register(SessionsGroup)
