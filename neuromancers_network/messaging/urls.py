from django.urls import path

from neuromancers_network.messaging import views

app_name = "messaging"

urlpatterns = [
    path("", views.InboxView.as_view(), name="inbox"),
    path("conversation/<uuid:pk>/", views.ConversationDetailView.as_view(), name="conversation-detail"),
    path("new/<uuid:user_id>/", views.NewConversationView.as_view(), name="new-conversation"),
]
