"""Duration-tier form field and repeater widget for meeting form pages.

Admins add a `duration_tiers` field to a meeting form page; the widget renders a
repeatable set of duration/price rows and uses htmx to append new rows from
``meetings.views.tier_row``. The cleaned value is a list of
``{"duration_minutes": int, "amount": Decimal | None}`` rows, reconciled onto
``MeetingPriceTier`` / ``MeetingPriceOption`` by ``apply_duration_tiers``.
"""

from __future__ import annotations

from decimal import Decimal
from decimal import InvalidOperation

from django import forms
from django.utils.translation import gettext_lazy as _

MIN_TIER_MINUTES = 5
MAX_TIER_MINUTES = 120


class DurationTiersWidget(forms.Widget):
    template_name = "meetings/widgets/duration_tiers.html"

    def value_from_datadict(self, data, files, name):
        durations = data.getlist(f"{name}-duration")
        amounts = data.getlist(f"{name}-amount")
        rows = []
        for index, duration in enumerate(durations):
            amount = amounts[index] if index < len(amounts) else ""
            if duration in (None, "") and amount in (None, ""):
                continue
            rows.append({"duration_minutes": duration, "amount": amount})
        return rows

    def format_value(self, value):
        return value or []

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["rows"] = context["widget"]["value"] or []
        return context


class DurationTiersField(forms.Field):
    """Validates a list of duration/price rows."""

    widget = DurationTiersWidget

    def clean(self, value):
        rows = super().clean(value) or []
        cleaned = []
        for row in rows:
            duration = row.get("duration_minutes")
            if duration in (None, ""):
                continue
            try:
                minutes = int(duration)
            except (TypeError, ValueError) as exc:
                raise forms.ValidationError(
                    _("Durations must be whole minutes."),
                ) from exc
            if not MIN_TIER_MINUTES <= minutes <= MAX_TIER_MINUTES:
                raise forms.ValidationError(
                    _("Durations must be between %(min)s and %(max)s minutes.")
                    % {"min": MIN_TIER_MINUTES, "max": MAX_TIER_MINUTES},
                )
            amount = row.get("amount")
            price = None
            if amount not in (None, ""):
                try:
                    price = Decimal(str(amount))
                except (InvalidOperation, TypeError, ValueError) as exc:
                    raise forms.ValidationError(
                        _("Prices must be numbers."),
                    ) from exc
            cleaned.append({"duration_minutes": minutes, "amount": price})
        return cleaned
