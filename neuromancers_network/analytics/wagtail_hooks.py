"""Admin URL, homepage panel and menu entry for analytics."""

from __future__ import annotations

from django.urls import path
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from neuromancers_network.analytics.panels import AnalyticsPanel
from neuromancers_network.analytics.views import AnalyticsDashboardView


@hooks.register("register_admin_urls")
def register_analytics_urls():
    return [
        path(
            "analytics/",
            AnalyticsDashboardView.as_view(),
            name="analytics_dashboard",
        ),
    ]


@hooks.register("construct_homepage_panels")
def add_analytics_panel(request, panels):
    panels.append(AnalyticsPanel())


@hooks.register("register_admin_menu_item")
def register_analytics_menu_item():
    return MenuItem(
        _("Analytics"),
        reverse("analytics_dashboard"),
        icon_name="site",
        order=600,
    )
