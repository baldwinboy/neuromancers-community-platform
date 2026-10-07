from django.conf import settings
from django.conf.urls.static import static
from django.urls import include
from django.urls import path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from neuromancers_network.core.views.calendar import CalendarFeedView

from .api import api

urlpatterns = [
    # DJ Stripe — includes webhook endpoint at /stripe/webhook/<uuid>/
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # Wagtail
    path("cms/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    # API base url
    path("api/", api.urls),
    # Wagtail DaisIE
    path("daisie/", include("wagtail_daisIE.dynamic.urls")),
    # DaisIE notifications (newsletter subscribe/unsubscribe)
    path("", include("wagtail_daisIE.notifications.urls")),
    # Read-only ICS calendar feed
    path(
        "calendar/<uuid:token>.ics",
        CalendarFeedView.as_view(),
        name="calendar_feed",
    ),
    # Media
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
    # Allauth
    path("", include("allauth.urls")),
    # Wagtail Pages (catch-all)
    path("", include(wagtail_urls)),
]

# Admin-designed error pages.
handler400 = "wagtail_daisIE.errors.handlers.handler400"
handler401 = "wagtail_daisIE.errors.handlers.handler401"
handler403 = "wagtail_daisIE.errors.handlers.handler403"
handler404 = "wagtail_daisIE.errors.handlers.handler404"
handler429 = "wagtail_daisIE.errors.handlers.handler429"
handler500 = "wagtail_daisIE.errors.handlers.handler500"
