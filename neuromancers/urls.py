from allauth import urls as allauth_urls
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from apps.accounts.views import ProfileView, UserView

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
    # Redirect 'accounts' path to default site
    re_path(
        r"^accounts/(?P<subpath>.*)$",
        RedirectView.as_view(
            pattern_name=None,  # Not using named URL pattern
            url="/%(subpath)s",  # Use the captured subpath in the redirect
            permanent=True,
        ),
        name="accounts_redirect",
    ),
    path("profile/", ProfileView.as_view(), name="accounts_profile"),
    path("profile/<str:username>", UserView.as_view(), name="accounts_user_profile"),
]

if settings.ENVIRONMENT == "development":
    urlpatterns = [
        path("django-admin/", admin.site.urls),
    ] + urlpatterns

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
]
