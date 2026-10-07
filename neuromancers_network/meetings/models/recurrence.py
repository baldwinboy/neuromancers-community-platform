import calendar
from datetime import timedelta

from django.db import models
from django.utils.translation import gettext_lazy as _

from neuromancers_network.core.models.base import Timestamped

from .choices import RecurrenceFrequency

_DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_ISO_WEEKDAYS = frozenset(range(1, 8))


class RecurrenceRule(Timestamped):
    frequency = models.CharField(
        _("Frequency"),
        max_length=10,
        choices=RecurrenceFrequency.choices,
    )
    interval = models.PositiveIntegerField(
        _("Interval"),
        default=1,
        help_text=_("How often the meeting repeats (e.g. every 2 weeks)."),
    )
    days_of_week = models.JSONField(
        _("Days of week"),
        default=list,
        blank=True,
        help_text=_(
            "List of ISO day numbers (1=Mon .. 7=Sun) for "
            "weekly/biweekly recurrences. "
            "Ignored for daily recurrences.",
        ),
    )
    end_date = models.DateField(
        _("End date"),
        null=True,
        blank=True,
        help_text=_("The recurrence stops on this date. Leave blank for no end."),
    )
    max_occurrences = models.PositiveIntegerField(
        _("Max occurrences"),
        null=True,
        blank=True,
        help_text=_(
            "Maximum number of occurrences. "
            "Leave blank for unlimited (until end_date).",
        ),
    )

    class Meta:
        verbose_name = "Recurrence rule"
        verbose_name_plural = "Recurrence rules"

    def _normalised_days(self) -> list[int]:
        """Return the configured ISO weekdays, ignoring out-of-range values."""
        days = []
        for value in self.days_of_week or []:
            try:
                day = int(value)
            except TypeError, ValueError:
                continue
            if day in _ISO_WEEKDAYS:
                days.append(day)
        return sorted(set(days))

    def __str__(self):
        parts = [f"Every {self.interval} {self.get_frequency_display()}"]
        days = self._normalised_days()
        if days:
            selected = [_DAY_NAMES[d - 1] for d in days]
            parts.append(f"on {', '.join(selected)}")
        if self.end_date:
            parts.append(f"until {self.end_date}")
        return " ".join(parts)

    def _next_daily(self, current):
        return current + timedelta(days=self.interval)

    def _next_weekly(self, current):
        candidate = current + timedelta(weeks=self.interval)
        days = self._normalised_days()
        if not days:
            return candidate
        while candidate.isoweekday() not in days:
            candidate += timedelta(days=1)
        return candidate

    def _next_biweekly(self, current):
        candidate = current + timedelta(weeks=2 * self.interval)
        days = self._normalised_days()
        if not days:
            return candidate
        while candidate.isoweekday() not in days:
            candidate += timedelta(days=1)
        return candidate

    def _next_monthly(self, current):
        month = current.month + self.interval
        year = current.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(current.day, max_day)
        return current.replace(year=year, month=month, day=day)

    def compute_next_occurrence(self, current_dt):
        dispatch = {
            RecurrenceFrequency.DAILY: self._next_daily,
            RecurrenceFrequency.WEEKLY: self._next_weekly,
            RecurrenceFrequency.BIWEEKLY: self._next_biweekly,
            RecurrenceFrequency.MONTHLY: self._next_monthly,
        }
        return dispatch[RecurrenceFrequency(self.frequency)](current_dt)

    def advance_meeting(self, meeting):
        if meeting.scheduled_at is None:
            return
        next_dt = self.compute_next_occurrence(meeting.scheduled_at)
        if self.end_date and next_dt.date() > self.end_date:
            return
        meeting.scheduled_at = next_dt
        meeting.save(update_fields=["scheduled_at"])
