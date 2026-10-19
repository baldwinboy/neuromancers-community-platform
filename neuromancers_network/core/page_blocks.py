"""Register project-contributed page blocks before daisIE builds its list.

daisIE snapshots its block list when ``wagtail_daisIE.pages`` is imported. This
module is imported at the top of ``core.models`` so the contribution is in place
first; registrations must stay import-order sensitive.
"""

from __future__ import annotations

from wagtail_daisIE.blocks.content import ALL_CONTENT_BLOCKS
from wagtail_daisIE.blocks.content_blocks import PAGE_CONTENT_BLOCKS

from neuromancers_network.analytics.blocks import MetricChartBlock

_METRIC_CHART_BLOCK = ("metric_chart", MetricChartBlock())

if "metric_chart" not in dict(PAGE_CONTENT_BLOCKS):
    PAGE_CONTENT_BLOCKS.append(_METRIC_CHART_BLOCK)
if "metric_chart" not in dict(ALL_CONTENT_BLOCKS):
    ALL_CONTENT_BLOCKS.append(_METRIC_CHART_BLOCK)
