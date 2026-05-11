from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from .api import api

# Non-translatable URLs
# Note: if you are using the Wagtail API or sitemaps,
# these should not be added to `i18n_patterns` either
urlpatterns = [
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("neuromancers_network.users.urls", namespace="users")),
    path("", include("allauth.urls")),
    # Cookie consent
    path("cookies/", include("cookie_consent.urls")),
    # Wagtail URLs
    path("cms/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    # DJ Stripe — includes webhook endpoint at /stripe/webhook/<uuid>/
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # Messaging
    path("messages/", include("neuromancers_network.messaging.urls", namespace="messaging")),
    # Events — Stripe Connect onboarding, checkout, subscription, account status
    path("events/", include("neuromancers_network.events.urls")),
]

# Translatable URLs
# These will be available under a language code prefix. For example /en/search/
urlpatterns += i18n_patterns(
    path("", include(wagtail_urls)),
    prefix_default_language=False,
)

# Translation / i18n
if "rosetta" in settings.INSTALLED_APPS:
    urlpatterns += [path("translations/", include("rosetta.urls"))]

# Media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# API URLS
urlpatterns += [
    # API base url
    path("api/", api.urls),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
