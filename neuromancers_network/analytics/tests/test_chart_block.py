from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime

import pytest
from wagtail_daisIE.blocks.content import ALL_CONTENT_BLOCKS
from wagtail_daisIE.blocks.content_blocks import PAGE_CONTENT_BLOCKS

from neuromancers_network.analytics.blocks import MetricChartBlock
from neuromancers_network.analytics.metrics import series_for_metric
from neuromancers_network.analytics.services import record_payment
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)


def _payment(month, day, minor):
    record_payment(
        session_id=f"cs_{month}_{day}",
        ref=f"request:{month}{day}",
        amount_minor=minor,
        currency="GBP",
        occurred_at=datetime(2026, month, day, 9, 0, tzinfo=UTC),
        payer=UserFactory(),
        payee=UserFactory(),
    )


class TestRegistration:
    def test_block_is_registered(self):
        assert "metric_chart" in dict(ALL_CONTENT_BLOCKS)
        assert "metric_chart" in dict(PAGE_CONTENT_BLOCKS)


class TestSeries:
    def test_series_is_monthly_and_oldest_first(self):
        _payment(4, 10, 1000)
        _payment(5, 10, 2500)

        series = series_for_metric("gbv", months=2, now=NOW)

        assert series["labels"] == ["Apr 2026", "May 2026"]
        assert series["values"] == [10.0, 25.0]

    def test_unknown_metric_raises(self):
        with pytest.raises(ValueError, match="Unknown series metric"):
            series_for_metric("nope", months=2, now=NOW)


class TestBlockContext:
    def test_context_contains_server_computed_data(self, monkeypatch):
        data_output = 25.0

        _payment(5, 10, 2500)
        monkeypatch.setattr(
            "neuromancers_network.analytics.metrics.timezone.now",
            lambda: NOW,
        )
        block = MetricChartBlock()
        value = block.to_python(
            {
                "title": "GBV",
                "metric": "gbv",
                "months": "3",
                "chart_type": "bar",
                "custom_colours": [],
                "settings": {},
            },
        )

        context = block.get_context(value)

        payload = json.loads(context["chart_datasets"])
        assert context["chart_title"] == "GBV"
        assert context["chart_type"] == "bar"
        assert payload["data"]["labels"]
        assert payload["data"]["datasets"][0]["data"][-1] == data_output
