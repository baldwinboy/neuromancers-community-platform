import calendar
import logging
from collections import defaultdict
from datetime import datetime
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db import transaction
from django.shortcuts import redirect

logger = logging.getLogger(__name__)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.contrib.routable_page.models import RoutablePageMixin
from wagtail.contrib.routable_page.models import route

from neuromancers_network.core.models import StyledPageMixin
from neuromancers_network.common.stripe import Stripe
from neuromancers_network.events.checkout import build_destination_checkout_params
from neuromancers_network.events.models import AvailabilityRule
from neuromancers_network.events.models import BookingStatus
from neuromancers_network.events.models import DurationPrice
from neuromancers_network.events.models import PaymentStatus
from neuromancers_network.events.models import Review
from neuromancers_network.events.models import Session
from neuromancers_network.events.models import SessionBooking
from neuromancers_network.events.models import SessionPrice
from neuromancers_network.events.models import SessionType

User = get_user_model()


def _host_or_staff(request, session):
    return request.user.is_authenticated and (
        request.user.is_staff or session.host == request.user
    )


class SessionPage(StyledPageMixin, RoutablePageMixin):
    page_description = _(
        "Use this page to customise the look of a session. All sessions will use the same design settings configured here.",
    )

    parent_page_types = ["core.HomePage", "core.StandardIndexPage"]
    subpage_types = []

    def get_context(self, request):
        context = super().get_context(request)
        return context

    def _get_session(self, session_id, request=None):
        qs = Session.objects.all()
        if request:
            qs = Session.objects.visible_for(request.user)
        try:
            return qs.get(id=session_id)
        except Session.DoesNotExist:
            return None

    def _visible(self, request, session):
        if session.is_published:
            return True
        return _host_or_staff(request, session)

    # --- Session detail ---

    @route(r"(?P<session_id>[\w-]+)/$")
    def session_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session or not self._visible(request, session):
            return self.render(request, template="404.html", status=404)

        return self.render(
            request,
            context_overrides={"session": session},
            template="events/session.html",
        )

    # --- Edit ---

    @route(r"(?P<session_id>[\w-]+)/edit/$")
    def session_edit_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session:
            return self.render(request, template="404.html", status=404)

        if not _host_or_staff(request, session):
            return self.render(request, template="404.html", status=404)

        if request.method == "POST":
            title = request.POST.get("title", "").strip()
            description = request.POST.get("description", "").strip()
            visibility = request.POST.get("visibility", "public")
            is_published = request.POST.get("is_published") == "on"

            errors = {}
            if not title:
                errors["title"] = _("Title is required.")

            if not errors:
                session.title = title
                session.description = description
                session.visibility = visibility
                session.is_published = is_published
                session.save()
                logger.info(
                    "Session %s updated by user %s", session.id, request.user.id,
                )
                return redirect(f"{self.url}{session.id}/")

            return self.render(
                request,
                context_overrides={"session": session, "errors": errors},
                template="events/session_edit.html",
            )

        return self.render(
            request,
            context_overrides={"session": session},
            template="events/session_edit.html",
        )

    # --- Helpers ---

    def _check_availability(self, host, starts_at, ends_at):
        """Verify the booking time falls within the host's availability rules."""
        if starts_at.date() != ends_at.date():
            return False
        rules = host.availability_rules.filter(is_active=True, day_of_week=starts_at.weekday())
        for rule in rules:
            if rule.start_time <= starts_at.time() and ends_at.time() <= rule.end_time:
                return True
        return rules.count() == 0  # no rules = no restriction

    def _calculate_amount(self, session, starts_at, ends_at):
        """Determine amount_due_subunit from DurationPrice for peer sessions."""
        duration_minutes = (ends_at - starts_at).total_seconds() / 60
        try:
            dp = session.duration_prices.get(duration_minutes=duration_minutes)
            return dp.amount_cents
        except DurationPrice.DoesNotExist:
            return None

    # --- Book ---

    @route(r"(?P<session_id>[\w-]+)/book/$")
    def session_booking_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session or not self._visible(request, session):
            return self.render(request, template="404.html", status=404)

        if not request.user.is_authenticated:
            return redirect(f"{self.url}{session.id}/")

        if request.user == session.host:
            return redirect(f"{self.url}{session.id}/")

        if request.method == "POST":
            starts_at_str = request.POST.get("starts_at", "")
            ends_at_str = request.POST.get("ends_at", "")
            timezone_str = request.POST.get("timezone", "UTC")
            accessibility_needs = request.POST.get("accessibility_needs", "")
            duration_minutes = request.POST.get("duration", "")

            errors = {}

            if not starts_at_str:
                errors["starts_at"] = _("Start time is required.")
            if not ends_at_str:
                errors["ends_at"] = _("End time is required.")

            starts_at = ends_at = None
            if starts_at_str:
                starts_at = datetime.fromisoformat(starts_at_str)
            if ends_at_str:
                ends_at = datetime.fromisoformat(ends_at_str)

            if starts_at and ends_at:
                if starts_at >= ends_at:
                    errors["ends_at"] = _("End time must be after start time.")

                if session.is_peer:
                    actual_minutes = (ends_at - starts_at).total_seconds() / 60
                    if session.min_duration_minutes and actual_minutes < session.min_duration_minutes:
                        errors["duration"] = _(
                            "Minimum booking duration is %(min)s minutes."
                        ) % {"min": session.min_duration_minutes}
                    if session.max_duration_minutes and actual_minutes > session.max_duration_minutes:
                        errors["duration"] = _(
                            "Maximum booking duration is %(max)s minutes."
                        ) % {"max": session.max_duration_minutes}

            if not errors:
                with transaction.atomic():
                    overlapping = SessionBooking.objects.select_for_update().filter(
                        session__host=session.host,
                        booking_status=BookingStatus.CONFIRMED,
                        starts_at__lt=ends_at,
                        ends_at__gt=starts_at,
                    ).exclude(
                        booking_status__in=[
                            BookingStatus.CANCELLED,
                            BookingStatus.COMPLETED,
                            BookingStatus.EXPIRED,
                        ],
                    ).exists() if session.is_peer else False

                    if overlapping:
                        errors["starts_at"] = _(
                            "This time slot overlaps with an existing booking."
                        )

                    if session.is_group:
                        spots_left = session.spots_remaining
                        if spots_left is not None and spots_left <= 0:
                            errors["capacity"] = _("This session is fully booked.")

                    if not errors:
                        if session.is_peer:
                            amount = self._calculate_amount(session, starts_at, ends_at)
                            if amount is None:
                                amount = 0
                        else:
                            amount = 0

                        booking = SessionBooking.objects.create(
                            session=session,
                            host=session.host,
                            attendee=request.user,
                            starts_at=starts_at,
                            ends_at=ends_at,
                            timezone=timezone_str,
                            accessibility_needs=accessibility_needs,
                            amount_due_subunit=amount,
                            currency=session.currency,
                        )
                        logger.info(
                            "Booking %s created for session %s by attendee %s",
                            booking.id, session.id, request.user.id,
                        )
                        if not session.require_approval:
                            if session.require_payment_before_joining:
                                booking.approve()
                                booking.save()
                            else:
                                booking.approve()
                                booking.confirm()
                                booking.save()
                        return redirect(f"{self.url}{session.id}/")

            return self.render(
                request,
                context_overrides={"session": session, "errors": errors},
                template="events/session_booking.html",
            )

        return self.render(
            request,
            context_overrides={"session": session},
            template="events/session_booking.html",
        )

    # --- Pay ---

    @route(r"(?P<session_id>[\w-]+)/pay/$")
    def session_payment_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session:
            return self.render(request, template="404.html", status=404)

        if not request.user.is_authenticated:
            return redirect(f"{self.url}{session.id}/")

        booking = SessionBooking.objects.accessible(
            request.user, session,
        ).filter(
            attendee=request.user,
            payment_status=PaymentStatus.REQUIRED,
        ).exclude(
            booking_status__in=[
                BookingStatus.CANCELLED,
                BookingStatus.COMPLETED,
                BookingStatus.EXPIRED,
            ],
        ).first()

        if request.method == "POST":
            if not booking:
                return redirect(f"{self.url}{session.id}/")

            stripe_helper = Stripe()
            success_url = request.build_absolute_uri(f"{self.url}{session.id}/")
            cancel_url = request.build_absolute_uri(f"{self.url}{session.id}/pay/")

            try:
                params = build_destination_checkout_params(
                    booking,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
                checkout_session = stripe_helper.client.Checkout.Session.create(
                    **params,
                )

                booking.initiate_checkout()
                booking.checkout_reference = checkout_session.id
                booking.save(update_fields=["payment_status", "checkout_reference"])

                logger.info(
                    "Checkout session %s created for booking %s by user %s",
                    checkout_session.id, booking.id, request.user.id,
                )
                return redirect(checkout_session.url)
            except Exception:
                return redirect(f"{self.url}{session.id}/pay/")

        return self.render(
            request,
            context_overrides={"session": session, "booking": booking},
            template="events/session_payment.html",
        )

    # --- Cancel booking ---

    @route(r"(?P<session_id>[\w-]+)/cancel/$")
    def session_cancel_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session or not session.is_published:
            return self.render(request, template="404.html", status=404)

        if not request.user.is_authenticated:
            return redirect(f"{self.url}{session.id}/")

        if request.method == "POST":
            booking = SessionBooking.objects.accessible(
                request.user, session,
            ).exclude(
                booking_status__in=[
                    BookingStatus.CANCELLED,
                    BookingStatus.COMPLETED,
                    BookingStatus.EXPIRED,
                ],
            ).filter(attendee=request.user).first()

            if booking:
                booking.cancel()
                booking.save()
                logger.info(
                    "Booking %s cancelled by user %s", booking.id, request.user.id,
                )
            return redirect(f"{self.url}{session.id}/")

        return self.render(
            request,
            context_overrides={"session": session},
            template="events/session_cancel.html",
        )

    # --- Reschedule ---

    @route(r"(?P<session_id>[\w-]+)/reschedule/$")
    def session_reschedule_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session or not session.is_published:
            return self.render(request, template="404.html", status=404)

        if not request.user.is_authenticated:
            return redirect(f"{self.url}{session.id}/")

        if request.method == "POST":
            from datetime import datetime

            booking = SessionBooking.objects.accessible(
                request.user, session,
            ).exclude(
                booking_status__in=[
                    BookingStatus.CANCELLED,
                    BookingStatus.COMPLETED,
                    BookingStatus.EXPIRED,
                ],
            ).filter(attendee=request.user).first()

            if booking:
                new_starts = request.POST.get("new_starts_at", "")
                new_ends = request.POST.get("new_ends_at", "")
                if new_starts and new_ends:
                    booking.starts_at = datetime.fromisoformat(new_starts)
                    booking.ends_at = datetime.fromisoformat(new_ends)
                    booking.save()

            return redirect(f"{self.url}{session.id}/")

        return self.render(
            request,
            context_overrides={"session": session},
            template="events/session_reschedule.html",
        )

    # --- Feedback ---

    @route(r"(?P<session_id>[\w-]+)/feedback/$")
    def session_feedback_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session or not session.is_published:
            return self.render(request, template="404.html", status=404)

        if not request.user.is_authenticated or request.user == session.host:
            return redirect(f"{self.url}{session.id}/")

        if request.method == "POST":
            rating = request.POST.get("rating")
            comment = request.POST.get("comment", "")
            if rating:
                try:
                    Review.objects.create(
                        session=session,
                        reviewer=request.user,
                        rating=int(rating),
                        comment=comment,
                    )
                except IntegrityError:
                    return self.render(
                        request,
                        context_overrides={
                            "session": session,
                            "errors": {"rating": _("You have already reviewed this session.")},
                        },
                        template="events/session_feedback.html",
                    )
                return redirect(f"{self.url}{session.id}/")
            return self.render(
                request,
                context_overrides={
                    "session": session,
                    "errors": {"rating": _("Rating is required.")},
                },
                template="events/session_feedback.html",
            )

        return self.render(
            request,
            context_overrides={"session": session},
            template="events/session_feedback.html",
        )

    # --- Reviews ---

    @route(r"(?P<session_id>[\w-]+)/reviews/$")
    def session_reviews_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session or not self._visible(request, session):
            return self.render(request, template="404.html", status=404)

        reviews = Review.objects.filter(session=session).order_by("-created_at")
        return self.render(
            request,
            context_overrides={
                "session": session,
                "reviews": reviews,
            },
            template="events/session_reviews.html",
        )

    # --- Participants (host only) ---

    @route(r"(?P<session_id>[\w-]+)/participants/$")
    def session_participants_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session:
            return self.render(request, template="404.html", status=404)

        if not _host_or_staff(request, session):
            return self.render(request, template="404.html", status=404)

        bookings = SessionBooking.objects.filter(session=session).order_by("starts_at")

        return self.render(
            request,
            context_overrides={"session": session, "bookings": bookings},
            template="events/session_participants.html",
        )

    # --- Approve booking (host only) ---

    @route(r"(?P<session_id>[\w-]+)/booking/(?P<booking_id>[\w-]+)/approve/$")
    def session_approve_booking_view(self, request, session_id, booking_id):
        session = self._get_session(session_id)
        if not session:
            return self.render(request, template="404.html", status=404)

        if not _host_or_staff(request, session):
            return self.render(request, template="404.html", status=404)

        if request.method == "POST":
            try:
                booking = SessionBooking.objects.get(id=booking_id, session=session)
                if booking.booking_status == BookingStatus.PENDING_APPROVAL:
                    booking.approve()
                    if not session.require_payment_before_joining:
                        booking.confirm()
                    booking.save()
            except SessionBooking.DoesNotExist:
                pass

        return redirect(f"{self.url}{session.id}/participants/")

    # --- Host bookings dashboard ---

    @route(r"^bookings/$")
    def session_bookings_view(self, request):
        if not request.user.is_authenticated:
            return redirect(self.url)

        bookings = SessionBooking.objects.filter(
            host=request.user,
        ).select_related(
            "session", "attendee",
        ).order_by("-starts_at")

        return self.render(
            request,
            context_overrides={"bookings": bookings},
            template="events/session_bookings.html",
        )

    # --- Availability rules ---

    @route(r"^availability/$")
    def session_availability_view(self, request):
        if not request.user.is_authenticated:
            return redirect(self.url)

        rules = AvailabilityRule.objects.filter(host=request.user).order_by("day_of_week", "start_time")

        if request.method == "POST":
            day_of_week = request.POST.get("day_of_week", "")
            start_time = request.POST.get("start_time", "")
            end_time = request.POST.get("end_time", "")

            errors = {}
            if not day_of_week:
                errors["day_of_week"] = _("Day of week is required.")
            if not start_time:
                errors["start_time"] = _("Start time is required.")
            if not end_time:
                errors["end_time"] = _("End time is required.")

            if start_time and end_time and start_time >= end_time:
                errors["end_time"] = _("End time must be after start time.")

            if not errors:
                AvailabilityRule.objects.create(
                    host=request.user,
                    day_of_week=int(day_of_week),
                    start_time=start_time,
                    end_time=end_time,
                )
                return redirect(f"{self.url}availability/")

            return self.render(
                request,
                context_overrides={"rules": rules, "errors": errors},
                template="events/session_availability.html",
            )

        return self.render(
            request,
            context_overrides={"rules": rules},
            template="events/session_availability.html",
        )

    # --- Delete availability rule ---

    @route(r"^availability/(?P<rule_id>\d+)/delete/$")
    def session_availability_delete_view(self, request, rule_id):
        if not request.user.is_authenticated:
            return redirect(self.url)

        try:
            rule = AvailabilityRule.objects.get(id=rule_id, host=request.user)
        except AvailabilityRule.DoesNotExist:
            return self.render(request, template="404.html", status=404)

        if request.method == "POST":
            rule.delete()
            return redirect(f"{self.url}availability/")

        return self.render(
            request,
            context_overrides={"rule": rule},
            template="events/session_availability_delete.html",
        )

    # --- Delete ---

    @route(r"(?P<session_id>[\w-]+)/delete/$")
    def session_delete_view(self, request, session_id):
        session = self._get_session(session_id)
        if not session:
            return self.render(request, template="404.html", status=404)

        if not _host_or_staff(request, session):
            return self.render(request, template="404.html", status=404)

        if request.method == "POST":
            confirmed = request.POST.get("confirm") == "on"
            if confirmed:
                logger.info(
                    "Session %s deleted by user %s", session.id, request.user.id,
                )
                session.delete()
                return redirect(self.url)
            return redirect(f"{self.url}{session.id}/")

        return self.render(
            request,
            context_overrides={"session": session},
            template="events/session_delete.html",
        )

    @route(r"^calendar/$")
    def session_calendar(self, request):
        year = request.GET.get("year")
        month = request.GET.get("month")

        today = timezone.now()
        if year and month:
            try:
                year = int(year)
                month = int(month)
            except (ValueError, TypeError):
                year, month = today.year, today.month
        else:
            year, month = today.year, today.month

        _, num_days = calendar.monthrange(year, month)
        first_weekday = datetime(year, month, 1).weekday()

        sessions = Session.objects.published().filter(
            starts_at__year=year,
            starts_at__month=month,
        ).select_related("host")

        events_by_day = defaultdict(list)
        for session in sessions:
            day = session.starts_at.day
            events_by_day[day].append(session)

        weeks = []
        week = [{"day": "", "in_month": False, "events": []} for _ in range(first_weekday)]
        for day in range(1, num_days + 1):
            week.append({
                "day": str(day),
                "in_month": True,
                "events": [
                    {
                        "title": s.title,
                        "url": f"{self.url}{s.id}/",
                        "is_group": s.is_group,
                    }
                    for s in events_by_day.get(day, [])
                ],
            })
            if len(week) == 7:
                weeks.append(week)
                week = []

        if week:
            while len(week) < 7:
                week.append({"day": "", "in_month": False, "events": []})
            weeks.append(week)

        prev_month = month - 1 or 12
        prev_year = year - 1 if prev_month == 12 else year
        next_month = month + 1 if month < 12 else 1
        next_year = year + 1 if next_month == 1 else year

        month_names = [
            "", _("January"), _("February"), _("March"), _("April"),
            _("May"), _("June"), _("July"), _("August"),
            _("September"), _("October"), _("November"), _("December"),
        ]

        return self.render(
            request,
            context_overrides={
                "calendar_weeks": weeks,
                "current_year": year,
                "current_month": month,
                "current_month_name": month_names[month],
                "prev_year": prev_year,
                "prev_month": prev_month,
                "next_year": next_year,
                "next_month": next_month,
            },
            template="events/session_calendar.html",
        )
