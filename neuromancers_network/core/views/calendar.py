from django.http import Http404
from django.http import HttpResponse
from django.views import View

from neuromancers_network.core.ical import build_ics
from neuromancers_network.core.models import CalendarFeedToken


class CalendarFeedView(View):
    """Serve a read-only ICS feed for the token owner's bookings."""

    def get(self, request, token):
        feed_token = (
            CalendarFeedToken.objects.filter(token=token, is_active=True)
            .select_related("user")
            .first()
        )
        if feed_token is None:
            raise Http404

        from neuromancers_network.meetings.models import BookingStatus  # noqa: PLC0415
        from neuromancers_network.meetings.models import MeetingStatus  # noqa: PLC0415

        bookings = (
            feed_token.user.bookings.filter(
                status__in=[BookingStatus.PENDING, BookingStatus.PAID],
                meeting__status=MeetingStatus.PUBLISHED,
            )
            .select_related("meeting")
            .prefetch_related("sessions")
        )
        response = HttpResponse(
            build_ics(bookings),
            content_type="text/calendar",
        )
        response["Content-Disposition"] = 'attachment; filename="neuromancers.ics"'
        return response
