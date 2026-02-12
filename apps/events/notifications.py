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
    platform_body=None,
    link_url=None,
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
        platform_body: Short plain-text message for on-platform notification display. If None, falls back to stripped email template.
        link_url: URL path for the notification's primary action (e.g., '/dashboard/')

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
        # Use platform_body for on-platform display, fall back to stripped email HTML
        body = platform_body or render_to_string(email_template, context)
        notification = Notifications.objects.create(
            sent_to=user,
            subject=subject_type,
            body=body,
            link_url=link_url,
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

    session_url = f"/sessions/{session.page.slug}/"
    context = {
        "user": session.host,
        "session": session,
        "session_url": session_url,
    }

    send_notification(
        user=session.host,
        subject_type=NotificationSubjectChoices.SESSION,
        email_subject=f"Your session '{session.title}' is now published",
        email_template="events/emails/session_published.html",
        context=context,
        peer_setting_key="published_session",
        platform_body=_(
            "Your session '%(title)s' is now live and visible to support seekers."
        )
        % {"title": session.title},
        link_url=session_url,
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

    attendee_name = (
        session_request.attendee.get_full_name() or session_request.attendee.username
    )

    send_notification(
        user=session_request.session.host,
        subject_type=NotificationSubjectChoices.SESSION,
        email_subject=f"New request for your session '{session_request.session.title}'",
        email_template="events/emails/session_requested.html",
        context=context,
        peer_setting_key="host_session_requested",
        platform_body=_(
            "%(attendee)s has requested to book '%(title)s'. "
            "Review and respond from your dashboard."
        )
        % {"attendee": attendee_name, "title": session_request.session.title},
        link_url="/dashboard/?tab=peer",
    )


def notify_session_approved(session_request):
    """Notify support seeker when host approves their session request"""
    try:
        settings = NotificationSettings.objects.get(user=session_request.attendee)
        if settings.responded_session == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    session_url = ""
    if session_request.session.is_published and hasattr(
        session_request.session, "page"
    ):
        session_url = f"/sessions/{session_request.session.page.slug}/"

    context = {
        "user": session_request.attendee,
        "session_request": session_request,
        "host": session_request.session.host,
        "session": session_request.session,
        "session_url": session_url,
    }

    host_name = (
        session_request.session.host.get_full_name()
        or session_request.session.host.username
    )

    send_notification(
        user=session_request.attendee,
        subject_type=NotificationSubjectChoices.SESSION,
        email_subject=f"Your request for '{session_request.session.title}' has been approved!",
        email_template="events/emails/session_approved.html",
        context=context,
        platform_body=_(
            "Your request for '%(title)s' with %(host)s has been approved! "
            "View your session details to get started."
        )
        % {"title": session_request.session.title, "host": host_name},
        link_url=session_url or "/profile/",
    )


def notify_session_rejected(session_request):
    """Notify support seeker when host rejects their session request"""
    try:
        settings = NotificationSettings.objects.get(user=session_request.attendee)
        if settings.responded_session == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    session_url = ""
    if session_request.session.is_published and hasattr(
        session_request.session, "page"
    ):
        session_url = f"/sessions/{session_request.session.page.slug}/"

    context = {
        "user": session_request.attendee,
        "session_request": session_request,
        "host": session_request.session.host,
        "session": session_request.session,
        "session_url": session_url,
    }

    host_name = (
        session_request.session.host.get_full_name()
        or session_request.session.host.username
    )

    rejection_info = ""
    if session_request.rejection_message:
        rejection_info = _(" Message: '%(message)s'") % {
            "message": session_request.rejection_message
        }

    send_notification(
        user=session_request.attendee,
        subject_type=NotificationSubjectChoices.SESSION,
        email_subject=_("Your request for '%(title)s' was not approved")
        % {"title": session_request.session.title},
        email_template="events/emails/session_rejected.html",
        context=context,
        platform_body=_(
            "Your request for '%(title)s' with %(host)s was not approved.%(rejection_info)s "
            "You can browse other available sessions."
        )
        % {
            "title": session_request.session.title,
            "host": host_name,
            "rejection_info": rejection_info,
        },
        link_url=session_url or "/sessions/",
    )


def notify_payment_made(session_request, amount_display=None):
    """Notify support seeker after successful payment"""
    try:
        settings = NotificationSettings.objects.get(user=session_request.attendee)
        if settings.payment_made == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    context = {
        "user": session_request.attendee,
        "session_request": session_request,
        "amount": amount_display or session_request.price,
        "session": session_request.session,
    }

    send_notification(
        user=session_request.attendee,
        subject_type=NotificationSubjectChoices.PAYMENT,
        email_subject=f"Payment confirmed for '{session_request.session.title}'",
        email_template="events/emails/payment_made.html",
        context=context,
        platform_body=_(
            "Your payment for '%(title)s' has been confirmed. "
            "You can view your receipt in payment history."
        )
        % {"title": session_request.session.title},
        link_url="/payments/history/",
    )


def notify_payment_received(session_request, amount_display=None):
    """Notify host when they receive a payment"""
    try:
        from apps.accounts.models_users.user_settings import PeerNotificationSettings

        peer_settings = PeerNotificationSettings.objects.get(
            user=session_request.session.host
        )
        if peer_settings.payment_received == NotificationChoices.NONE:
            return
    except PeerNotificationSettings.DoesNotExist:
        pass

    attendee_name = (
        session_request.attendee.get_full_name() or session_request.attendee.username
    )

    context = {
        "user": session_request.session.host,
        "session_request": session_request,
        "amount": amount_display or session_request.price,
        "attendee": session_request.attendee,
        "session": session_request.session,
    }

    send_notification(
        user=session_request.session.host,
        subject_type=NotificationSubjectChoices.PAYMENT,
        email_subject=f"Payment received for '{session_request.session.title}'",
        email_template="events/emails/payment_received.html",
        context=context,
        peer_setting_key="payment_received",
        platform_body=_(
            "%(attendee)s has paid for '%(title)s'. "
            "The payment has been transferred to your Stripe account."
        )
        % {"attendee": attendee_name, "title": session_request.session.title},
        link_url="/settings/?tab=stripe",
    )


def notify_refund_requested(session_request):
    """Notify host when a refund is requested"""
    try:
        from apps.accounts.models_users.user_settings import PeerNotificationSettings

        peer_settings = PeerNotificationSettings.objects.get(
            user=session_request.session.host
        )
        if peer_settings.payment_refund_request == NotificationChoices.NONE:
            return
    except PeerNotificationSettings.DoesNotExist:
        pass

    attendee_name = (
        session_request.attendee.get_full_name() or session_request.attendee.username
    )

    context = {
        "user": session_request.session.host,
        "session_request": session_request,
        "amount": session_request.price,
        "attendee": session_request.attendee,
        "session": session_request.session,
        "reason": "",
    }

    send_notification(
        user=session_request.session.host,
        subject_type=NotificationSubjectChoices.PAYMENT,
        email_subject=f"Refund requested for '{session_request.session.title}'",
        email_template="events/emails/refund_requested.html",
        context=context,
        peer_setting_key="payment_refund_request",
        platform_body=_(
            "%(attendee)s has requested a refund for '%(title)s'. "
            "Review the request from your dashboard."
        )
        % {"attendee": attendee_name, "title": session_request.session.title},
        link_url="/dashboard/?tab=refunds",
    )


def notify_refund_approved(session_request):
    """Notify seeker when their refund request is approved"""
    try:
        settings = NotificationSettings.objects.get(user=session_request.attendee)
        if settings.payment_made == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    email_settings = get_email_template_settings()
    context = {
        "user": session_request.attendee,
        "session_request": session_request,
        "amount": session_request.price,
        "session": session_request.session,
        "greeting": email_settings["refund_approved_greeting"],
        "body": email_settings["refund_approved_body"],
    }

    send_notification(
        user=session_request.attendee,
        subject_type=NotificationSubjectChoices.PAYMENT,
        email_subject=f"Your refund for '{session_request.session.title}' has been approved",
        email_template="events/emails/refund_approved.html",
        context=context,
        platform_body=_(
            "Your refund for '%(title)s' has been approved. "
            "The amount will be returned to your original payment method within 5-10 business days."
        )
        % {"title": session_request.session.title},
        link_url="/payments/history/",
    )


def notify_request_revoked(session_request):
    """Notify attendee when the host revokes their approved request."""
    try:
        settings = NotificationSettings.objects.get(user=session_request.attendee)
        if settings.responded_session == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    host_name = (
        session_request.session.host.get_full_name()
        or session_request.session.host.username
    )

    context = {
        "user": session_request.attendee,
        "session_request": session_request,
        "session": session_request.session,
        "host": session_request.session.host,
    }

    send_notification(
        user=session_request.attendee,
        subject_type=NotificationSubjectChoices.SESSION,
        email_subject=f"Your request for '{session_request.session.title}' has been revoked",
        email_template="events/emails/request_revoked.html",
        context=context,
        platform_body=_(
            "%(host)s has revoked your approved request for '%(title)s'. "
            "If a payment was made, a refund will be processed automatically."
        )
        % {"host": host_name, "title": session_request.session.title},
        link_url="/profile/",
    )
