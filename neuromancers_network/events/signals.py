import logging

logger = logging.getLogger(__name__)


def log_booking_creation(sender, instance, created, **kwargs):
    """Log whenever a booking is created or its status changes."""
    from neuromancers_network.events.models import BookingStatus  # noqa: PLC0415
    from neuromancers_network.events.models import PaymentStatus  # noqa: PLC0415

    if created:
        logger.info(
            "Booking %s created for session %s by attendee %s",
            instance.id,
            instance.session_id,
            instance.attendee_id,
        )
        if instance.booking_status == BookingStatus.CONFIRMED:
            from neuromancers_network.events.tasks import send_booking_notification

            send_booking_notification.delay(str(instance.id))
    else:
        logger.info(
            "Booking %s updated: status=%s payment=%s",
            instance.id,
            instance.booking_status,
            instance.payment_status,
        )
        if instance.payment_status == PaymentStatus.PAID:
            from neuromancers_network.events.tasks import (  # noqa: PLC0415
                send_payment_received_notification,
            )

            send_payment_received_notification.delay(str(instance.id))
        if instance.booking_status == BookingStatus.COMPLETED:
            from neuromancers_network.events.tasks import send_review_prompt

            send_review_prompt.delay(str(instance.id))
