from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from ninja import NinjaAPI
from ninja.security import SessionAuth

from neuromancers_network.core.bootstrap_state import current_status

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


def _json(payload: dict[str, str], *, status: int = 200) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


@api.get("/ready", auth=None)
def ready(request: HttpRequest) -> JsonResponse:
    revision = settings.GIT_COMMIT_SHA
    if not settings.BOOTSTRAP_GATE_ENABLED:
        return _json({"status": "ready", "revision": revision})

    status = current_status()
    http_status = 200 if status.serving_allowed else 503
    public_status = "ready" if status.serving_allowed else status.phase.value
    return _json(
        {"status": public_status, "revision": revision},
        status=http_status,
    )
