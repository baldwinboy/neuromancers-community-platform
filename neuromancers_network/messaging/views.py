from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import View

from neuromancers_network.messaging.models import Conversation
from neuromancers_network.messaging.models import Message


class InboxView(LoginRequiredMixin, ListView):
    template_name = "messaging/inbox.html"
    context_object_name = "conversations"

    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user,
        ).prefetch_related("participants").order_by("-updated_at")


class ConversationDetailView(LoginRequiredMixin, DetailView):
    model = Conversation
    template_name = "messaging/conversation_detail.html"
    context_object_name = "conversation"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def post(self, request, *args, **kwargs):
        conversation = self.get_object()
        body = request.POST.get("body", "").strip()
        if body:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=body,
            )
        return redirect(
            reverse("messaging:conversation-detail", kwargs={"pk": conversation.pk}),
        )


class NewConversationView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        other_user = get_object_or_404(User, id=user_id)

        if other_user == request.user:
            return redirect("messaging:inbox")

        existing = Conversation.objects.filter(
            participants=request.user,
        ).filter(participants=other_user).first()

        if existing:
            return redirect(
                reverse("messaging:conversation-detail", kwargs={"pk": existing.pk}),
            )

        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)

        body = request.POST.get("body", "").strip()
        if body:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=body,
            )

        return redirect(
            reverse("messaging:conversation-detail", kwargs={"pk": conversation.pk}),
        )
