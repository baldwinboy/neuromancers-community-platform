from django.contrib import admin

from neuromancers_network.messaging.models import Conversation
from neuromancers_network.messaging.models import Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["sender", "body", "created_at", "read_at"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["subject", "created_at", "updated_at"]
    filter_horizontal = ["participants"]
    inlines = [MessageInline]
