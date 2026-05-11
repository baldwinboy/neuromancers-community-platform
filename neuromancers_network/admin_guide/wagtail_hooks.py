from django.conf import settings
from django.urls import path
from django.urls import reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .views import GuideViewSet
from .views import OnboardingTaskPanel
from .views import OnboardingTaskViewSet
from .views import StripeSyncView


@hooks.register("register_admin_viewset")
def register_admin_guide_viewset():
    return GuideViewSet()


@hooks.register("register_admin_viewset")
def register_onboarding_viewset():
    return OnboardingTaskViewSet()


@hooks.register("construct_homepage_panels")
def add_onboarding_task_panel(request, panels):
    panels.append(OnboardingTaskPanel())


@hooks.register("register_admin_menu_item")
def register_webhook_endpoint_menu_item():
    admin_url = getattr(settings, "ADMIN_URL", "admin/")
    return MenuItem(
        "Stripe Webhook Endpoints",
        f"/{admin_url}djstripe/webhookendpoint/",
        classname="",
        icon_name="link-external",
        order=9000,
    )


@hooks.register("register_admin_urls")
def register_stripe_sync_url():
    return [
        path(
            "stripe-sync/",
            StripeSyncView.as_view(),
            name="admin_guide_stripe_sync",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_stripe_sync_menu_item():
    return MenuItem(
        "Manual Stripe Sync",
        reverse("admin_guide_stripe_sync"),
        classname="",
        icon_name="cogs",
        order=9001,
    )
