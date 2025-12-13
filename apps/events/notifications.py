"""
Notification utilities for sending emails based on user preferences.

Integrates with the NotificationSettings and PeerNotificationSettings models
to respect user communication preferences (Web only, Email, All, or None).
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from wagtail.contrib.settings.registry import registry

from apps.accounts.models_users.user_settings import (
    NotificationChoices,
    Notifications,
    NotificationSettings,
    NotificationSubjectChoices,
    PeerNotificationSettings,
)


def get_email_template_settings(request=None):
    """
    Load EventEmailTemplateSettings for use in notification context.

    Returns settings dict with greeting and body text for each email type.
    Provides sensible defaults if settings don't exist or are not configured.
    """
    try:
        settings = registry.get_by_natural_key("core", "EmailTemplateSettings")
        settings = settings.load(request)
        return {
            "session_published_greeting": settings.session_published_greeting,
            "session_published_body": settings.session_published_body,
            "session_requested_greeting": settings.session_requested_greeting,
            "session_requested_body": settings.session_requested_body,
            "session_approved_greeting": settings.session_approved_greeting,
            "session_approved_body": settings.session_approved_body,
            "payment_made_greeting": settings.payment_made_greeting,
            "payment_made_body": settings.payment_made_body,
            "payment_received_greeting": settings.payment_received_greeting,
            "payment_received_body": settings.payment_received_body,
            "refund_requested_greeting": settings.refund_requested_greeting,
            "refund_requested_body": settings.refund_requested_body,
            "refund_requested_note": settings.refund_requested_note,
            "refund_approved_greeting": settings.refund_approved_greeting,
            "refund_approved_body": settings.refund_approved_body,
        }
    except Exception:
        # Fallback if settings don't exist or are not loaded
        return {
            "session_published_greeting": _(
                "Congratulations! Your session has been published."
            ),
            "session_published_body": _(
                "Your session is now visible to support seekers. Support seekers can now request sessions with you. Check your notifications regularly for new requests."
            ),
            "session_requested_greeting": _(
                "A support seeker has requested to book your session."
            ),
            "session_requested_body": _(
                "Review this request and either approve or decline it."
            ),
            "session_approved_greeting": _(
                "Great news! Your request has been approved."
            ),
            "session_approved_body": _(
                "Your session is now confirmed. Please arrive a few minutes early. If you have any questions, reach out to your host."
            ),
            "payment_made_greeting": _(
                "Thank you for your payment! Your session is now confirmed."
            ),
            "payment_made_body": _(
                "Your payment has been securely processed through Stripe. You'll receive a separate confirmation email from Stripe with your receipt."
            ),
            "payment_received_greeting": _(
                "You've received a payment for your session!"
            ),
            "payment_received_body": _(
                "The payment has been processed and transferred to your connected Stripe account. You can view your payment history and balance in your account dashboard."
            ),
            "refund_requested_greeting": _(
                "A support seeker has requested a refund for their session payment."
            ),
            "refund_requested_body": _(
                "Please review this request and decide whether to approve or decline the refund. You can manage this in your account."
            ),
            "refund_requested_note": _(
                "Note: You're not required to approve this refund, but doing so helps maintain a positive experience for support seekers."
            ),
            "refund_approved_greeting": _(
                "Good news! Your refund request has been approved."
            ),
            "refund_approved_body": _(
                "We appreciate your understanding. If you have any feedback about your experience, we'd love to hear from you."
            ),
        }


def send_notification(
    user,
    subject_type,
    email_subject,
    email_template,
    context,
    peer_setting_key=None,
    request=None,
):
    """
    Send a notification to a user based on their preferences.

    Args:
        user: The User to notify
        subject_type: NotificationSubjectChoices value (ACCOUNT, PAYMENT, SESSION, REMINDER)
        email_subject: Subject line for the email
        email_template: Path to email template (e.g., 'events/emails/session_reminder.html')
        context: Dictionary of context variables for the template
        peer_setting_key: If this is for a peer host, the PeerNotificationSettings field name (e.g., 'payment_received')
        request: Django request object (used to load Wagtail settings and build site URL)

    Returns:
        Notification object if created, None otherwise
    """
    try:
        # Get notification preference
        if peer_setting_key:
            # Peer-specific notification
            peer_settings = PeerNotificationSettings.objects.get(user=user)
            preference = getattr(
                peer_settings, peer_setting_key, NotificationChoices.WEB_ONLY
            )
        else:
            # General notification
            settings = NotificationSettings.objects.get(user=user)
            # Map subject type to preference field
            preference_map = {
                NotificationSubjectChoices.ACCOUNT: "account_deleted",
                NotificationSubjectChoices.PAYMENT: "payment_made",
                NotificationSubjectChoices.SESSION: "responded_session",
                NotificationSubjectChoices.REMINDER: "session_reminders",
            }
            preference = getattr(
                settings,
                preference_map.get(subject_type, "account_deleted"),
                NotificationChoices.WEB_ONLY,
            )
    except (NotificationSettings.DoesNotExist, PeerNotificationSettings.DoesNotExist):
        # Default to WEB_ONLY if no settings
        preference = NotificationChoices.WEB_ONLY

    # Add site_url to context if not already present
    if "site_url" not in context and request:
        context["site_url"] = request.build_absolute_uri("/")

    # Create web notification if preference allows
    if preference in [NotificationChoices.WEB_ONLY, NotificationChoices.ALL]:
        notification = Notifications.objects.create(
            sent_to=user,
            subject=subject_type,
            body=render_to_string(email_template, context),
        )
    else:
        notification = None

    # Send email if preference allows
    if preference in [NotificationChoices.EMAIL, NotificationChoices.ALL]:
        try:
            # Get email settings from Wagtail
            settings = registry.get_by_natural_key(
                "contact", "ContactEmailSettings"
            ).load(request)
            email_from = settings.default_sender or None
            email_body = render_to_string(email_template, context)
            send_mail(
                subject=email_subject,
                message=email_body,
                from_email=email_from,
                recipient_list=[user.email],
                fail_silently=False,
                html_message=email_body,
            )
        except Exception as e:
            print(f"Error sending email to {user.email}: {str(e)}")

    return notification


def notify_session_published(session):
    """Notify peers when a session is published"""
    try:
        from apps.accounts.models_users.user_settings import PeerNotificationSettings

        peer_settings = PeerNotificationSettings.objects.get(user=session.host)
        if peer_settings.published_session == NotificationChoices.NONE:
            return
    except PeerNotificationSettings.DoesNotExist:
        pass

    if not hasattr(session, "page"):
        return

    context = {
        "user": session.host,
        "session": session,
        "session_url": f"/sessions/{session.page.slug}/",
    }

    send_notification(
        user=session.host,
        subject_type=NotificationSubjectChoices.SESSION,
        email_subject=f"Your session '{session.title}' is now published",
        email_template="events/emails/session_published.html",
        context=context,
        peer_setting_key="published_session",
    )


def notify_session_requested(session_request):
    """Notify host when a support seeker requests their session"""
    try:
        from apps.accounts.models_users.user_settings import PeerNotificationSettings

        peer_settings = PeerNotificationSettings.objects.get(
            user=session_request.session.host
        )
        if peer_settings.host_session_requested == NotificationChoices.NONE:
            return
    except PeerNotificationSettings.DoesNotExist:
        pass

    if not session_request.session.is_published or not hasattr(
        session_request.session, "page"
    ):
        return

    context = {
        "user": session_request.session.host,
        "session_request": session_request,
        "attendee": session_request.attendee,
        "session": session_request.session,
        "approve_url": f"/sessions/{session_request.session.page.slug}/requests/{session_request.id}/approve/",
    }

    send_notification(
        user=session_request.session.host,
        subject_type=NotificationSubjectChoices.SESSION,
        email_subject=f"New request for your session '{session_request.session.title}'",
        email_template="events/emails/session_requested.html",
        context=context,
        peer_setting_key="host_session_requested",
    )


def notify_session_approved(session_request):
    """Notify support seeker when host approves their session request"""
    try:
        settings = NotificationSettings.objects.get(user=session_request.attendee)
        if settings.responded_session == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    if not session_request.session.is_published or not hasattr(
        session_request.session, "page"
    ):
        return

    context = {
        "user": session_request.attendee,
        "session_request": session_request,
        "host": session_request.session.host,
        "session": session_request.session,
        "session_url": f"/sessions/{session_request.session.page.slug}/",
    }

    send_notification(
        user=session_request.attendee,
        subject_type=NotificationSubjectChoices.SESSION,
        email_subject=f"Your request for '{session_request.session.title}' has been approved!",
        email_template="events/emails/session_approved.html",
        context=context,
    )


def notify_payment_made(payment):
    """Notify support seeker after successful payment"""
    try:
        settings = NotificationSettings.objects.get(user=payment.user)
        if settings.payment_made == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    context = {
        "user": payment.user,
        "payment": payment,
        "amount": payment.amount,
        "session": payment.session_request.session,
    }

    send_notification(
        user=payment.user,
        subject_type=NotificationSubjectChoices.PAYMENT,
        email_subject=f"Payment confirmed for '{payment.session_request.session.title}'",
        email_template="events/emails/payment_made.html",
        context=context,
    )


def notify_payment_received(payment):
    """Notify host when they receive a payment"""
    try:
        from apps.accounts.models_users.user_settings import PeerNotificationSettings

        peer_settings = PeerNotificationSettings.objects.get(
            user=payment.session_request.session.host
        )
        if peer_settings.payment_received == NotificationChoices.NONE:
            return
    except PeerNotificationSettings.DoesNotExist:
        pass

    context = {
        "user": payment.session_request.session.host,
        "payment": payment,
        "amount": payment.amount,
        "attendee": payment.user,
        "session": payment.session_request.session,
    }

    send_notification(
        user=payment.session_request.session.host,
        subject_type=NotificationSubjectChoices.PAYMENT,
        email_subject=f"Payment received for '{payment.session_request.session.title}'",
        email_template="events/emails/payment_received.html",
        context=context,
        peer_setting_key="payment_received",
    )


def notify_refund_requested(refund_request):
    """Notify host when a refund is requested"""
    try:
        from apps.accounts.models_users.user_settings import PeerNotificationSettings

        peer_settings = PeerNotificationSettings.objects.get(user=refund_request.host)
        if peer_settings.payment_refund_request == NotificationChoices.NONE:
            return
    except PeerNotificationSettings.DoesNotExist:
        pass

    context = {
        "user": refund_request.host,
        "refund_request": refund_request,
        "amount": refund_request.payment.amount,
        "attendee": refund_request.payment.user,
        "session": refund_request.payment.session_request.session,
        "reason": refund_request.reason,
    }

    send_notification(
        user=refund_request.host,
        subject_type=NotificationSubjectChoices.PAYMENT,
        email_subject=f"Refund requested for '{refund_request.payment.session_request.session.title}'",
        email_template="events/emails/refund_requested.html",
        context=context,
        peer_setting_key="payment_refund_request",
    )


def notify_refund_approved(refund_request):
    """Notify seeker when their refund request is approved"""
    try:
        settings = NotificationSettings.objects.get(user=refund_request.payment.user)
        if settings.payment_made == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    email_settings = get_email_template_settings()
    context = {
        "user": refund_request.payment.user,
        "refund_request": refund_request,
        "amount": refund_request.payment.amount,
        "session": refund_request.payment.session_request.session,
        "greeting": email_settings["refund_approved_greeting"],
        "body": email_settings["refund_approved_body"],
    }

    send_notification(
        user=refund_request.payment.user,
        subject_type=NotificationSubjectChoices.PAYMENT,
        email_subject=f"Your refund for '{refund_request.payment.session_request.session.title}' has been approved",
        email_template="events/emails/refund_approved.html",
        context=context,
    )
