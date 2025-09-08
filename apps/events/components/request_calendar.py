import calendar
from collections import defaultdict
from datetime import datetime

from django_components import Component, register

def get_calendar_for_availability(available_slots: list[tuple[datetime, datetime]]):
    grouped = defaultdict(list)
    active_date_times = defaultdict(list)

    for start, end in available_slots:
        start_date = start.date()
        grouped[(start.year, start.month)].append(start_date)
        active_date_times[start_date.isoformat()] += [[start.hour, start.minute], [end.hour, end.minute]]

    cal = calendar.Calendar()
    calendar_data = []

    for (year, month), dates in sorted(grouped.items()):
        month_days = cal.monthdatescalendar(year, month)
        calendar_data.append(
            {
                "year": year,
                "month_int": month,
                "month_name": calendar.month_name[month],
                "month_days": month_days,
                "active_dates": set(dates),
                "active_date_times": dict(active_date_times),
            }
        )

    return calendar_data


@register("request_calendar")
class RequestCalendar(Component):
    template_file = "includes/request_calendar.html"
    js_file = "js/request_calendar.js"

    def get_template_data(self, args, kwargs, slots, context):
        calendar_data = get_calendar_for_availability(self.kwargs["available_slots"])
        durations = [int(i) for i in self.kwargs["durations"].split(",")]
        return {
            "calendar_data": calendar_data,
            "available_slots": self.kwargs["available_slots"],
            "durations": durations
        }
