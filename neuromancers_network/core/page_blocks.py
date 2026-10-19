"""Register project-contributed page blocks before daisIE builds its list.

daisIE snapshots its block list when ``wagtail_daisIE.pages`` is imported. This
module is imported at the top of ``core.models`` so the contribution is in place
first; registrations must stay import-order sensitive.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail_daisIE.blocks.content import ALL_CONTENT_BLOCKS
from wagtail_daisIE.blocks.content_blocks import PAGE_CONTENT_BLOCKS

from neuromancers_network.analytics.blocks import MetricChartBlock


class CookieRegistryBlock(blocks.StaticBlock):
    """Render the active cookie registry grouped by category."""

    def get_context(self, value, parent_context=None):
        from neuromancers_network.core.models import Cookie  # noqa: PLC0415
        from neuromancers_network.core.models import CookieCategory  # noqa: PLC0415

        context = super().get_context(value, parent_context)
        groups = []
        for category, label in CookieCategory.choices:
            rows = list(Cookie.objects.filter(is_active=True, category=category))
            if rows:
                groups.append(
                    {"value": category, "label": label, "cookies": rows},
                )
        context["cookie_groups"] = groups
        return context

    class Meta:
        icon = "cog"
        label = _("Cookie registry")
        template = "core/blocks/cookie_registry.html"


_METRIC_CHART_BLOCK = ("metric_chart", MetricChartBlock())
_COOKIE_REGISTRY_BLOCK = ("cookie_registry", CookieRegistryBlock())

if "metric_chart" not in dict(PAGE_CONTENT_BLOCKS):
    PAGE_CONTENT_BLOCKS.append(_METRIC_CHART_BLOCK)
if "metric_chart" not in dict(ALL_CONTENT_BLOCKS):
    ALL_CONTENT_BLOCKS.append(_METRIC_CHART_BLOCK)
if "cookie_registry" not in dict(PAGE_CONTENT_BLOCKS):
    PAGE_CONTENT_BLOCKS.append(_COOKIE_REGISTRY_BLOCK)
if "cookie_registry" not in dict(ALL_CONTENT_BLOCKS):
    ALL_CONTENT_BLOCKS.append(_COOKIE_REGISTRY_BLOCK)
