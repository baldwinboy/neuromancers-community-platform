"""Admin-authored metric chart block (server-computed series)."""

from __future__ import annotations

import json

from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtailcharts.blocks import CHART_TYPES
from wagtailcharts.blocks import ChartSettingsBlock

DAISYUI_PALETTE = (
    "#570df8",
    "#f000b8",
    "#37cdbe",
    "#3d4451",
    "#f87272",
    "#36d399",
    "#fbbd23",
    "#0ea5e9",
)

METRIC_CHOICES = (
    ("gbv", _("Gross booking value")),
    ("application_fees", _("Application fees")),
    ("refunds", _("Refunds")),
    ("payments", _("Payments")),
    ("active_members", _("Active members")),
    ("active_peers", _("Active peers")),
    ("subscription_revenue", _("Subscription revenue")),
    ("session_minutes", _("Session minutes")),
)

MONTH_CHOICES = (
    ("3", _("Last 3 months")),
    ("6", _("Last 6 months")),
    ("12", _("Last 12 months")),
)

METRIC_LABELS = dict(METRIC_CHOICES)


class MetricChartBlock(blocks.StructBlock):
    """A chart of a platform metric over recent UTC calendar months."""

    title = blocks.CharBlock(required=False)
    metric = blocks.ChoiceBlock(choices=METRIC_CHOICES, default="gbv")
    months = blocks.ChoiceBlock(choices=MONTH_CHOICES, default="6")
    chart_type = blocks.ChoiceBlock(choices=CHART_TYPES, default="bar")
    custom_colours = blocks.ListBlock(
        blocks.CharBlock(),
        required=False,
        help_text=_("Optional chart colours appended to the DaisyUI palette."),
    )
    settings = ChartSettingsBlock()

    def get_context(self, value, parent_context=None):
        from neuromancers_network.analytics.metrics import series_for_metric  # noqa: PLC0415

        context = super().get_context(value, parent_context)
        series = series_for_metric(value["metric"], months=int(value["months"]))
        palette = [
            *DAISYUI_PALETTE,
            *[colour for colour in value["custom_colours"] if colour],
        ]
        colours = [
            palette[index % len(palette)] for index in range(len(series["values"]))
        ]
        label = str(METRIC_LABELS[value["metric"]])
        datasets = {
            "data": {
                "labels": series["labels"],
                "datasets": [
                    {
                        "label": label,
                        "data": series["values"],
                        "backgroundColor": colours,
                        "borderColor": colours,
                        "borderWidth": 2,
                    },
                ],
            },
            "options": {},
        }
        settings = value["settings"]
        chart_config = getattr(settings, "config", json.dumps(dict(settings)))
        context.update(
            {
                "chart_datasets": json.dumps(datasets),
                "chart_config": chart_config,
                "chart_type": value["chart_type"],
                "chart_title": value["title"] or label,
            },
        )
        return context

    class Meta:
        icon = "fa-chart"
        label = _("Metric chart")
        group = _("Analytics")
        template = "analytics/blocks/metric_chart.html"
