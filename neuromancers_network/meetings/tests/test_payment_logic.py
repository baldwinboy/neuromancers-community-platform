"""Pure (no-database) tests for payment helper logic."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from neuromancers_network.meetings.models.booking import _group_by_peer_currency
from neuromancers_network.meetings.models.booking import _line_item
from neuromancers_network.meetings.models.refund import _to_minor_units
from neuromancers_network.meetings.signals import _line_item_refs
from neuromancers_network.payments.charges import adaptive_pricing_for_source

TEN_POUNDS_MINOR = 1000


def _booking(peer_id: int, currency: str):
    meeting = SimpleNamespace(peer_id=peer_id, currency=currency)
    return SimpleNamespace(meeting=meeting)


class TestToMinorUnits:
    def test_converts_major_units(self):
        assert _to_minor_units("10.00") == TEN_POUNDS_MINOR

    def test_rejects_non_positive(self):
        with pytest.raises(ValueError, match="greater than zero"):
            _to_minor_units("0")

    def test_rejects_invalid(self):
        with pytest.raises(ValueError, match="not a valid number"):
            _to_minor_units("abc")


class TestLineItemRefs:
    def test_parses_refs(self):
        session_data = {"metadata": {"line_item_refs": "request:1,booking:2"}}

        assert _line_item_refs(session_data) == ["request:1", "booking:2"]

    def test_missing_metadata(self):
        assert _line_item_refs({}) == []
        assert _line_item_refs({"metadata": None}) == []


class TestGroupByPeerCurrency:
    def test_groups_by_peer_and_currency(self):
        bookings = [
            _booking(1, "GBP"),
            _booking(1, "USD"),
            _booking(2, "GBP"),
        ]

        groups = _group_by_peer_currency(bookings)

        assert set(groups) == {(1, "GBP"), (1, "USD"), (2, "GBP")}
        assert groups[(1, "GBP")] == [bookings[0]]


class TestAdaptivePricing:
    def test_stripe_source_enables(self):
        assert adaptive_pricing_for_source("stripe") == {"enabled": True}

    def test_other_source_disables(self):
        assert adaptive_pricing_for_source("manual") is None


class TestLineItem:
    def test_shape(self):
        meeting = SimpleNamespace(currency="GBP", title="Session")

        assert _line_item(meeting, 1000) == {
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": "Session"},
                "unit_amount": 1000,
            },
            "quantity": 1,
        }
