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
    REVIEW_PENDING_APPROVAL = (
        "review_pending_approval",
        _("Review pending approval"),
    )
    REVIEW_PUBLISHED = "review_published", _("Review published")
    REVIEW_HIDDEN = "review_hidden", _("Review hidden")

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
    SUBSCRIPTION_PAUSED = "subscription_paused", _("Subscription paused")
    SUBSCRIPTION_RESUMED = "subscription_resumed", _("Subscription resumed")

    # Payments
    PAYMENT_REMINDER_DUE = "payment_reminder_due", _("Payment reminder due")

    # Meetings
    MEETING_UPCOMING = "meeting_upcoming", _("Upcoming meeting")
    MEETING_CANCELLED = "meeting_cancelled", _("Cancelled meeting")
    MEETING_UNPUBLISHED = "meeting_unpublished", _("Meeting unpublished")
    MEETINGS_UNPUBLISHED = "meetings_unpublished", _("Meetings unpublished")
    MEETINGS_DELETED = "meetings_deleted", _("Meetings deleted")

    # Session reminders
    SESSION_REMINDER_1D = "session_reminder_1d", _("Session reminder (1 day)")
    SESSION_REMINDER_1H = "session_reminder_1h", _("Session reminder (1 hour)")

    # Accounts
    ACCOUNT_CREATED = "account_created", _("Account created")
    ACCOUNT_DELETED = "account_deleted", _("Account deleted")
    ACCOUNT_DEGRADED = "account_degraded", _("Account degraded")
    ACCOUNT_DEACTIVATED = "account_deactivated", _("Account deactivated")
    ACCOUNT_REACTIVATED = "account_reactivated", _("Account reactivated")
    ACCOUNT_DELETION_SCHEDULED = (
        "account_deletion_scheduled",
        _("Account deletion scheduled"),
    )
    ACCOUNT_DELETION_CANCELLED = (
        "account_deletion_cancelled",
        _("Account deletion cancelled"),
    )

    # Identity
    EMAIL_CHANGED = "email_changed", _("Email address changed")
    USERNAME_CHANGED = "username_changed", _("Username changed")

    # Blocking (member-to-member safety)
    USER_BLOCKED = "user_blocked", _("Member blocked")
    USER_UNBLOCKED = "user_unblocked", _("Member unblocked")

    # Moderation (platform-wide bans)
    IP_BANNED = "ip_banned", _("IP address banned")
    IP_UNBANNED = "ip_unbanned", _("IP address unbanned")
    EMAIL_BANNED = "email_banned", _("Email address banned")
    EMAIL_UNBANNED = "email_unbanned", _("Email address unbanned")
    REPORT_CREATED = "report_created", _("Report created")
    REPORT_RESOLVED = "report_resolved", _("Report resolved")
    REPORT_REJECTED = "report_rejected", _("Report rejected")

    # Privacy / data
    DATA_EXPORT_REQUESTED = "data_export_requested", _("Data export requested")
    DATA_EXPORT_READY = "data_export_ready", _("Data export ready")

    # Peer publishing
    PEER_PUBLISHED_MEETING = (
        "peer_published_meeting",
        _("Care provider published a meeting"),
    )

    # Payments
    PAYMENT_SUCCEEDED = "payment_succeeded", _("Payment succeeded")
    PAYMENT_FAILED = "payment_failed", _("Payment failed")


def notification_event_choices():
    """Lazy ``choices`` callable for :class:`NotificationEventType`.

    Passing a callable keeps ``Field.deconstruct`` storing the function
    reference rather than a materialised list, so growing the enum does not
    trigger a migration. This function is referenced by historical migrations
    and must stay at a stable module path.
    """
    return NotificationEventType.choices
