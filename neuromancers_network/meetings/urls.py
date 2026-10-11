from django.urls import path

from neuromancers_network.meetings.views import tier_row

app_name = "meetings"

urlpatterns = [
    path("tiers/row/", tier_row, name="tier_row"),
]
