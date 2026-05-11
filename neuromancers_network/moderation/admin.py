from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from neuromancers_network.moderation.models import Flag
from neuromancers_network.moderation.models import FlagRule


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = [
        "content_type", "object_id", "reason", "status", "flagger", "created_at",
    ]
    list_filter = ["status", "reason", "content_type"]
    search_fields = ["object_id", "description"]
    readonly_fields = ["flagger", "content_type", "object_id", "created_at"]
    actions = ["dismiss_flags", "uphold_flags"]

    def dismiss_flags(self, request, queryset):
        queryset.update(status="dismissed", reviewed_by=request.user)
    dismiss_flags.short_description = _("Dismiss selected flags")

    def uphold_flags(self, request, queryset):
        queryset.update(status="upheld", reviewed_by=request.user)
    uphold_flags.short_description = _("Uphold selected flags")


@admin.register(FlagRule)
class FlagRuleAdmin(admin.ModelAdmin):
    list_display = ["pattern", "content_type", "field", "reason", "is_active"]
    list_filter = ["is_active", "content_type", "reason"]
    search_fields = ["pattern"]
