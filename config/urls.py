from django.conf import settings
from django.conf.urls.static import static
from django.urls import include
from django.urls import path
from django.views.generic import RedirectView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from neuromancers_network.core.views.calendar import CalendarFeedView
from neuromancers_network.core.views.consent import accept_consent
from neuromancers_network.core.views.consent import reset_consent
from neuromancers_network.core.views.provider_webhooks import daily_webhook
from neuromancers_network.core.views.provider_webhooks import whereby_webhook
from neuromancers_network.meetings.views import PaymentCancelledView
from neuromancers_network.meetings.views import PaymentSuccessView
from neuromancers_network.moderation.views import AccountDeletionCancelView
from neuromancers_network.moderation.views import DataExportDownloadView

from .api import api

urlpatterns = [
    # DJ Stripe — includes webhook endpoint at /stripe/webhook/<uuid>/
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # Wagtail
    path("cms/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    # API base url
    path("api/", api.urls),
    # Provider meeting webhooks (signature-verified)
    path("webhooks/whereby/", whereby_webhook, name="whereby_webhook"),
    path("consent/accept/", accept_consent, name="consent_accept"),
    path("consent/reset/", reset_consent, name="consent_reset"),
    path("webhooks/daily/", daily_webhook, name="daily_webhook"),
    # Signed account-deletion cancellation link
    path(
        "account/deletion/cancel/<str:token>/",
        AccountDeletionCancelView.as_view(),
        name="account_deletion_cancel",
    ),
    # Private data-export download (signed, owner/staff only)
    path(
        "exports/<int:pk>/<str:token>/",
        DataExportDownloadView.as_view(),
        name="data_export_download",
    ),
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
    # Stripe Checkout return pages
    path(
        "pay/success/",
        PaymentSuccessView.as_view(),
        name="payment_success",
    ),
    path(
        "pay/cancelled/",
        PaymentCancelledView.as_view(),
        name="payment_cancelled",
    ),
    # App-owned Dashboard section forms
    path("dashboard/forms/", include("neuromancers_network.users.settings")),
    path(
        "settings/",
        RedirectView.as_view(url="/dashboard/", permanent=True),
        name="settings_redirect",
    ),
    path(
        "signup/",
        RedirectView.as_view(pattern_name="account_signup", permanent=False),
        name="signup_shortcut",
    ),
    # htmx fragments for meeting form pages (duration-tier repeater)
    path("meetings/", include("neuromancers_network.meetings.urls")),
    # Media
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
    # Allauth
    path("", include("allauth.urls")),
    # Wagtail Pages (catch-all)
    path("", include(wagtail_urls)),
]

if getattr(settings, "DEBUG", False):
    try:
        import debug_toolbar

        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    except ImportError:
        pass

# Admin-designed error pages.
handler400 = "wagtail_daisIE.errors.handlers.handler400"
handler401 = "wagtail_daisIE.errors.handlers.handler401"
handler403 = "wagtail_daisIE.errors.handlers.handler403"
handler404 = "wagtail_daisIE.errors.handlers.handler404"
handler429 = "wagtail_daisIE.errors.handlers.handler429"
handler500 = "wagtail_daisIE.errors.handlers.handler500"
