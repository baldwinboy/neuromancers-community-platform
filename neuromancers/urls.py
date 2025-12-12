from allauth import urls as allauth_urls
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from apps.accounts.views import (
    ClearNotificationsView,
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationInboxView,
    ProfileView,
    StripeAuthorizeCallbackView,
    StripeAuthorizeView,
    StripeDisconnectView,
    UserSettingsView,
    UserView,
)
from apps.events.views import (
    ApproveRefundView,
    CreatePaymentIntentView,
    PaymentHistoryView,
    PaymentSuccessView,
    RequestRefundView,
)

# Load all other app admins
admin.autodiscover()

urlpatterns = [
    # Redirect admin login/logout to default
    re_path(
        r"^admin/(?P<action>login|logout)/(?P<subpath>.*)$",
        RedirectView.as_view(
            pattern_name=None,  # Not using named URL pattern
            url="/%(action)s/%(subpath)s",  # Use the captured subpath in the redirect
            permanent=True,
        ),
        name="admin_login_logout_redirect",
    ),
    path("admin/", include(wagtailadmin_urls), name="wagtailadmin"),
    path("documents/", include(wagtaildocs_urls), name="wagtaildocs"),
    # For Django REST Framework
    path("api-auth/", include("rest_framework.urls"), name="drf"),
    # Redirect 'accounts' or 'home' path to default site
    re_path(
        r"^(accounts|home)/(?P<subpath>.*)$",
        RedirectView.as_view(
            pattern_name=None,  # Not using named URL pattern
            url="/%(subpath)s",  # Use the captured subpath in the redirect
            permanent=True,
        ),
        name="accounts_redirect",
    ),
    path("profile/", ProfileView.as_view(), name="accounts_profile"),
    path("profile/<str:username>", UserView.as_view(), name="accounts_user_profile"),
    path("settings/", UserSettingsView.as_view(), name="accounts_user_settings"),
    path("notifications/", NotificationInboxView.as_view(), name="notification_inbox"),
    path(
        "notifications/<uuid:notification_id>/mark-read/",
        MarkNotificationReadView.as_view(),
        name="mark_notification_read",
    ),
    path(
        "notifications/mark-all-read/",
        MarkAllNotificationsReadView.as_view(),
        name="mark_all_notifications_read",
    ),
    path(
        "notifications/clear/",
        ClearNotificationsView.as_view(),
        name="clear_notifications",
    ),
    path("stripe/authorize/", StripeAuthorizeView.as_view(), name="stripe_authorize"),
    path(
        "stripe/oauth/callback/",
        StripeAuthorizeCallbackView.as_view(),
        name="stripe_authorize_callback",
    ),
    path(
        "stripe/disconnect/", StripeDisconnectView.as_view(), name="stripe_disconnect"
    ),
    # Payment URLs
    path("payments/history/", PaymentHistoryView.as_view(), name="payment_history"),
    path("payments/success/", PaymentSuccessView.as_view(), name="payment_success"),
    path(
        "payments/create/<uuid:request_id>/",
        CreatePaymentIntentView.as_view(),
        name="create_payment_intent",
    ),
    path(
        "payments/refund/<uuid:request_id>/",
        RequestRefundView.as_view(),
        name="request_refund",
    ),
    path(
        "payments/approve-refund/<uuid:request_id>/",
        ApproveRefundView.as_view(),
        name="approve_refund",
    ),
]

if settings.ENVIRONMENT == "development":
    urlpatterns = (
        [
            path("django-admin/", admin.site.urls),
        ]
        + urlpatterns
        + debug_toolbar_urls()
    )

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Django Allauth for user management
    path("", include(allauth_urls)),
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
    # Components
    path("", include("django_components.urls")),
]
