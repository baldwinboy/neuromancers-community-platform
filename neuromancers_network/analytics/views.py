"""Staff-only analytics dashboard."""

from __future__ import annotations

from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from wagtail.admin.auth import require_admin_access
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from neuromancers_network.analytics.metrics import PERIOD_THIS_MONTH
from neuromancers_network.analytics.metrics import PERIODS
from neuromancers_network.analytics.metrics import RevenueSummary
from neuromancers_network.analytics.metrics import platform_metrics


@method_decorator(require_admin_access, name="dispatch")
class AnalyticsDashboardView(WagtailAdminTemplateMixin, TemplateView):
    """Render platform metrics for a selectable UTC calendar period."""

    template_name = "analytics/dashboard.html"
    page_title = _("Analytics")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.request.GET.get("period") or PERIOD_THIS_MONTH
        if period not in PERIODS:
            period = PERIOD_THIS_MONTH
        metrics = platform_metrics(period=period)
        revenue = RevenueSummary(
            marketplace=metrics["application_fees"],
            subscription=metrics["subscription_revenue"],
        )
        context.update(
            {
                "period": period,
                "periods": [
                    (value, value.replace("_", " ").title()) for value in PERIODS
                ],
                "metrics": metrics,
                "revenue": revenue,
            },
        )
        return context
