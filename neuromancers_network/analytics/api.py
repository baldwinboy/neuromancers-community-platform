"""Read-only analytics API (staff platform scope, member self scope)."""

from __future__ import annotations

from decimal import Decimal

from ninja import Router
from ninja.errors import HttpError

from neuromancers_network.analytics.metrics import PERIOD_THIS_MONTH
from neuromancers_network.analytics.metrics import PERIODS
from neuromancers_network.analytics.metrics import member_metrics
from neuromancers_network.analytics.metrics import peer_metrics
from neuromancers_network.analytics.metrics import platform_metrics

router = Router(tags=["analytics"])


def _jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _valid_period(period: str) -> str:
    if period not in PERIODS:
        message = f"Unknown analytics period {period!r}"
        raise HttpError(400, message)
    return period


def _require_staff(request) -> None:
    user = request.user
    if not (user.is_staff or user.is_superuser):
        raise HttpError(403, "Staff only")


@router.get("/platform")
def platform(request, period: str = PERIOD_THIS_MONTH):
    _require_staff(request)
    return _jsonable(platform_metrics(period=_valid_period(period)))


@router.get("/me")
def me(request, period: str = PERIOD_THIS_MONTH):
    period = _valid_period(period)
    result = member_metrics(request.user, period=period)
    if getattr(request.user, "peer_profile", None) is not None:
        result = {
            **result,
            "peer": _jsonable(
                peer_metrics(request.user, period=period),
            ),
        }
    return _jsonable(result)
