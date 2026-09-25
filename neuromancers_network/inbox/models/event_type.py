from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationEventType(models.TextChoices):
    """Domain events recorded by the internal event bus.

    Each member names a business event that may warrant a user notification.
    Wagtail admins will later choose which of these to listen to and how to
    render them; this enum is the canonical, closed set of such events.
    """

    # Bookings (MeetingRequest lifecycle)
    BOOKING_REQUESTED = "booking_requested", _("Booking requested")
    BOOKING_APPROVED = "booking_approved", _("Booking approved")
    BOOKING_REJECTED = "booking_rejected", _("Booking rejected")
    BOOKING_PAID = "booking_paid", _("Booking paid")
    BOOKING_COMPLETED = "booking_completed", _("Booking completed")
    BOOKING_CANCELLED = "booking_cancelled", _("Booking cancelled")

    # Refunds (RefundRequest lifecycle)
    REFUND_REQUESTED = "refund_requested", _("Refund requested")
    REFUND_APPROVED = "refund_approved", _("Refund approved")
    REFUND_REJECTED = "refund_rejected", _("Refund rejected")
    REFUND_REFUNDED = "refund_refunded", _("Refund issued")

    # Reviews
    REVIEW_CREATED = "review_created", _("Review created")

    # Peer approval
    PEER_APPROVED = "peer_approved", _("Peer approved")
    PEER_APPLICATION_APPROVED = (
        "peer_application_approved",
        _(
            "Peer application approved",
        ),
    )
    PEER_APPLICATION_REJECTED = (
        "peer_application_rejected",
        _(
            "Peer application rejected",
        ),
    )

    # Subscriptions
    SUBSCRIPTION_CREATED = "subscription_created", _("Subscription created")
    SUBSCRIPTION_CANCELLED = "subscription_cancelled", _("Subscription cancelled")

    # Payments
    PAYMENT_REMINDER_DUE = "payment_reminder_due", _("Payment reminder due")

    # Meetings
    MEETING_UPCOMING = "meeting_upcoming", _("Upcoming meeting")
    MEETING_CANCELLED = "meeting_cancelled", _("Cancelled meeting")

    # Session reminders
    SESSION_REMINDER_1D = "session_reminder_1d", _("Session reminder (1 day)")
    SESSION_REMINDER_1H = "session_reminder_1h", _("Session reminder (1 hour)")

    # Accounts
    ACCOUNT_CREATED = "account_created", _("Account created")
    ACCOUNT_DELETED = "account_deleted", _("Account deleted")
    ACCOUNT_DEGRADED = "account_degraded", _("Account degraded")

    # Peer publishing
    PEER_PUBLISHED_MEETING = (
        "peer_published_meeting",
        _("Care provider published a meeting"),
    )

    # Payments
    PAYMENT_SUCCEEDED = "payment_succeeded", _("Payment succeeded")
    PAYMENT_FAILED = "payment_failed", _("Payment failed")
