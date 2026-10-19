"""Admin homepage panel for analytics."""

from __future__ import annotations

from django.urls import reverse
from wagtail.admin.ui.components import Component

from neuromancers_network.analytics.metrics import PERIOD_THIS_MONTH
from neuromancers_network.analytics.metrics import RevenueSummary
from neuromancers_network.analytics.metrics import platform_metrics


class AnalyticsPanel(Component):
    name = "analytics"
    order = 160
    template_name = "analytics/panel.html"

    def get_context_data(self, parent_context):
        metrics = platform_metrics(period=PERIOD_THIS_MONTH)
        return {
            "analytics_url": reverse("analytics_dashboard"),
            "revenue": RevenueSummary(
                marketplace=metrics["application_fees"],
                subscription=metrics["subscription_revenue"],
            ),
        }
