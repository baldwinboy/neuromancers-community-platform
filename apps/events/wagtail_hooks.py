from django.dispatch import receiver
from guardian.admin import GuardedModelAdmin
from wagtail.signals import page_published
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .form_fields import WagtailAdminFiltersMultipleChoiceField
from .models import (
    GroupSession,
    GroupSessionRequest,
    PeerSession,
    PeerSessionRequest,
    SessionsIndexPage,
)


@receiver(page_published)
def enforce_sessions_slug(sender, instance, **kwargs):
    if isinstance(instance, SessionsIndexPage) and instance.slug != "sessions":
        instance.slug = "sessions"
        instance.save()
        # Publish only if needed
        if not instance.live:
            instance.save_revision().publish()


class PeerSessionAdmin(SnippetViewSet, GuardedModelAdmin):
    model = PeerSession
    icon = "radio-empty"
    list_display = ("title", "host")
    list_filter = ("host",)
    search_fields = ("title", "host")

    def get_edit_handler(self):
        # Import here to avoid circular imports
        from wagtail.admin.panels import FieldPanel, ObjectList

        edit_handler = ObjectList(
            [
                FieldPanel("title"),
                FieldPanel("description"),
                FieldPanel("host"),
                FieldPanel("languages"),
                FieldPanel("durations"),
                FieldPanel("currency"),
                FieldPanel("price"),
                FieldPanel("concessionary_price"),
                FieldPanel("per_hour_price"),
                FieldPanel("concessionary_per_hour_price"),
                FieldPanel("access_before_payment"),
                FieldPanel("require_request_approval"),
                FieldPanel("require_concessionary_approval"),
                FieldPanel("require_refund_approval"),
                FieldPanel("allow_custom_price"),
                FieldPanel("filters", widget=WagtailAdminFiltersMultipleChoiceField),
                FieldPanel("is_published"),
            ]
        )
        return edit_handler.bind_to_model(self.model)


class GroupSessionAdmin(SnippetViewSet, GuardedModelAdmin):
    model = GroupSession
    icon = "radio-full"
    list_display = ("title", "host")
    list_filter = ("host",)
    search_fields = ("title", "host")

    def get_edit_handler(self):
        from wagtail.admin.panels import FieldPanel, ObjectList

        edit_handler = ObjectList(
            [
                FieldPanel("title"),
                FieldPanel("description"),
                FieldPanel("host"),
                FieldPanel("language"),
                FieldPanel("starts_at"),
                FieldPanel("ends_at"),
                FieldPanel("capacity"),
                FieldPanel("currency"),
                FieldPanel("price"),
                FieldPanel("concessionary_price"),
                FieldPanel("access_before_payment"),
                FieldPanel("require_request_approval"),
                FieldPanel("require_concessionary_approval"),
                FieldPanel("require_refund_approval"),
                FieldPanel("allow_custom_price"),
                FieldPanel("recurring"),
                FieldPanel("recurrence_type"),
                FieldPanel("recurrence_ends_at"),
                FieldPanel("filters", widget=WagtailAdminFiltersMultipleChoiceField),
                FieldPanel("is_published"),
                FieldPanel("meeting_link"),
            ]
        )
        return edit_handler.bind_to_model(self.model)


class PeerSessionRequestAdmin(SnippetViewSet, GuardedModelAdmin):
    model = PeerSessionRequest
    icon = "mail"
    list_display = ("session", "attendee", "starts_at", "ends_at")
    list_filter = ("session", "attendee", "starts_at", "ends_at", "status")
    search_fields = (
        "session",
        "attendee",
    )


class GroupSessionRequestAdmin(SnippetViewSet, GuardedModelAdmin):
    model = GroupSessionRequest
    icon = "folder-open-1"
    list_display = ("session", "attendee")
    list_filter = ("session", "attendee", "status")
    search_fields = (
        "session",
        "attendee",
    )


class SessionsGroup(SnippetViewSetGroup):
    menu_label = "Sessions"
    icon = "calendar-alt"
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (
        PeerSessionAdmin,
        PeerSessionRequestAdmin,
        GroupSessionAdmin,
        GroupSessionRequestAdmin,
    )


register_snippet(SessionsGroup)
