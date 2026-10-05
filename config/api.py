from django.contrib.auth.decorators import user_passes_test
from ninja import NinjaAPI
from ninja.security import SessionAuth

staff_required = user_passes_test(lambda u: u.is_active and u.is_staff)

api = NinjaAPI(
    urls_namespace="api",
    auth=SessionAuth(),
    docs_decorator=staff_required,
)

api.add_router("/users/", "neuromancers_network.users.api.views.router")
api.add_router("/peers/", "neuromancers_network.peers.api.router")
api.add_router("/meetings/", "neuromancers_network.meetings.api.router")


@api.get("/health", auth=None)
def health(request):
    return {"status": "ok"}
