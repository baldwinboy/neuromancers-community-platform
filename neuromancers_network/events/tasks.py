from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from neuromancers_network.emails.utils import send_db_email
from neuromancers_network.events.models import BookingStatus
from neuromancers_network.events.models import SessionBooking

logger = logging.getLogger(__name__)


@shared_task
def send_booking_notification(booking_id: str) -> None:
    """Send booking confirmation/notification to attendee and host."""
    try:
        booking = SessionBooking.objects.select_related(
            "attendee", "host", "session",
        ).get(id=booking_id)
    except SessionBooking.DoesNotExist:
        logger.error("Booking %s not found for notification", booking_id)
        return

    context = {
        "session_title": booking.session.title,
        "attendee_name": booking.attendee.get_full_name() or booking.attendee.username,
        "host_name": booking.host.get_full_name() or booking.host.username,
        "starts_at": booking.starts_at.isoformat(),
        "ends_at": booking.ends_at.isoformat(),
        "booking_id": str(booking.id),
    }

    send_db_email(
        to=[booking.attendee.email],
        template_name="session_booked_attendee",
        context=context,
    )
    send_db_email(
        to=[booking.host.email],
        template_name="session_booked_host",
        context=context,
    )


@shared_task
def send_payment_received_notification(booking_id: str) -> None:
    """Notify attendee and host that payment was received."""
    try:
        booking = SessionBooking.objects.select_related(
            "attendee", "host", "session",
        ).get(id=booking_id)
    except SessionBooking.DoesNotExist:
        return

    context = {
        "session_title": booking.session.title,
        "amount": booking.amount_due_subunit,
        "currency": booking.currency,
    }

    send_db_email(
        to=[booking.attendee.email],
        template_name="payment_received_attendee",
        context=context,
    )
    send_db_email(
        to=[booking.host.email],
        template_name="payment_received_host",
        context=context,
    )


@shared_task
def send_session_reminder(booking_id: str) -> None:
    """Send reminder to attendee 24h before session."""
    try:
        booking = SessionBooking.objects.select_related(
            "attendee", "host", "session",
        ).get(id=booking_id)
    except SessionBooking.DoesNotExist:
        return

    context = {
        "session_title": booking.session.title,
        "host_name": booking.host.get_full_name() or booking.host.username,
        "starts_at": booking.starts_at.isoformat(),
        "meeting_link": booking.meeting_link or "",
    }

    send_db_email(
        to=[booking.attendee.email],
        template_name="session_reminder",
        context=context,
    )


@shared_task
def send_review_prompt(booking_id: str) -> None:
    """Prompt attendee to leave a review after session completion."""
    try:
        booking = SessionBooking.objects.select_related(
            "attendee", "session",
        ).get(id=booking_id)
    except SessionBooking.DoesNotExist:
        return

    context = {
        "session_title": booking.session.title,
        "session_id": str(booking.session.id),
    }

    send_db_email(
        to=[booking.attendee.email],
        template_name="review_prompt",
        context=context,
    )


@shared_task
def expire_stale_bookings() -> None:
    """Expire bookings past their payment window (cron task)."""
    cutoff = timezone.now() - timedelta(hours=24)
    stale = SessionBooking.objects.filter(
        booking_status=BookingStatus.PENDING_APPROVAL,
        created_at__lt=cutoff,
    )
    for booking in stale:
        try:
            booking.expire_approval()
            booking.save()
        except Exception:
            logger.exception("Failed to expire booking %s", booking.id)

    stale_payment = SessionBooking.objects.filter(
        payment_status__in=["checkout_created", "processing"],
        updated_at__lt=cutoff,
    )
    for booking in stale_payment:
        try:
            booking.expire_payment()
            booking.save()
        except Exception:
            logger.exception("Failed to expire payment for booking %s", booking.id)
