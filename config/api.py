from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from ninja import NinjaAPI
from ninja.security import SessionAuth

if TYPE_CHECKING:
    from django.http import HttpRequest

staff_required = user_passes_test(lambda u: u.is_active and u.is_staff)

api = NinjaAPI(
    urls_namespace="api",
    auth=SessionAuth(),
    docs_decorator=staff_required,
)

api.add_router("/users/", "neuromancers_network.users.api.views.router")
api.add_router("/peers/", "neuromancers_network.peers.api.router")
api.add_router("/meetings/", "neuromancers_network.meetings.api.router")
api.add_router("/analytics/", "neuromancers_network.analytics.api.router")


@api.get("/health", auth=None)
def health(request: HttpRequest) -> dict[str, str]:
    return {"status": "ok", "revision": settings.GIT_COMMIT_SHA}
