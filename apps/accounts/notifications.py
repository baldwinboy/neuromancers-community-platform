"""
Account-related notification utilities.

Handles notifications for account creation, closure, and role changes.
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from wagtail.contrib.settings.registry import registry

from apps.accounts.models_users.user_settings import (
    NotificationChoices,
    NotificationSettings,
)


def get_account_email_template_settings(request=None):
    """
    Load AccountEmailTemplateSettings for use in notification context.

    Returns settings dict with greeting and body text for account emails.
    Provides sensible defaults if settings don't exist or are not configured.
    """
    try:
        settings = registry.get_by_natural_key("core", "EmailTemplateSettings").load(
            request
        )
        return {
            "account_created_greeting": settings.account_created_greeting,
            "account_created_body": settings.account_created_body,
            "account_closed_greeting": settings.account_closed_greeting,
            "account_closed_body": settings.account_closed_body,
            "account_closed_note": settings.account_closed_note,
            "group_upgrade_greeting": settings.group_upgrade_greeting,
            "group_upgrade_body": settings.group_upgrade_body,
            "group_downgrade_greeting": settings.group_downgrade_greeting,
            "group_downgrade_body": settings.group_downgrade_body,
        }
    except Exception:
        # Fallback if settings don't exist or are not loaded
        return {
            "account_created_greeting": _(
                "Your account has been created successfully. Welcome to our community!"
            ),
            "account_created_body": _(
                "Start by exploring sessions, connecting with peers, or setting up your profile. If you have any questions, our support team is here to help."
            ),
            "account_closed_greeting": _(
                "We're sorry to see you go. Your account has been closed as requested."
            ),
            "account_closed_body": _(
                "If you have any questions about your account closure or need to retrieve any information, please contact our support team within 30 days of this notice."
            ),
            "account_closed_note": _(
                "We hope to see you in the community again someday!"
            ),
            "group_upgrade_greeting": _(
                "Congratulations! You've been upgraded to a Peer in the Neuromancers community."
            ),
            "group_upgrade_body": _(
                "As a Peer, you can now create sessions and share your expertise with support seekers. Complete your profile and set up your session offerings to get started."
            ),
            "group_downgrade_greeting": _("Your account role has been updated."),
            "group_downgrade_body": _(
                "Your role has been updated in our community. Please review your account settings to see what features are available to you."
            ),
        }


def notify_account_created(user, request=None):
    """Notify user when their account is created"""
    try:
        settings = NotificationSettings.objects.get(user=user)
        if settings.account_deleted == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    email_settings = get_account_email_template_settings(request)
    context = {
        "user": user,
        "greeting": email_settings["account_created_greeting"],
        "body": email_settings["account_created_body"],
        "site_url": request.build_absolute_uri("/") if request else "",
    }

    # Get email from settings
    try:
        settings = registry.get_by_natural_key("contact", "ContactEmailSettings").load(
            request
        )
        email_from = settings.default_sender
    except Exception:
        email_from = None

    # Send email
    try:
        email_body = render_to_string("account/email/account_created.html", context)
        send_mail(
            subject=_("Welcome to Neuromancers"),
            message=email_body,
            from_email=email_from,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=email_body,
        )
    except Exception:
        pass


def notify_account_closed(user, request=None):
    """Notify user when their account is closed"""
    email_settings = get_account_email_template_settings(request)
    context = {
        "user": user,
        "greeting": email_settings["account_closed_greeting"],
        "body": email_settings["account_closed_body"],
        "note": email_settings["account_closed_note"],
        "closure_date": user.updated_at if hasattr(user, "updated_at") else "today",
        "site_url": request.build_absolute_uri("/") if request else "",
    }

    # Get email from settings
    try:
        settings = registry.get_by_natural_key("contact", "ContactEmailSettings").load(
            request
        )
        email_from = settings.default_sender
    except Exception:
        email_from = None

    # Send email
    try:
        email_body = render_to_string("account/email/account_closed.html", context)
        send_mail(
            subject=_("Your Account Has Been Closed"),
            message=email_body,
            from_email=email_from,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=email_body,
        )
    except Exception:
        pass


def notify_group_status_changed(user, is_upgrade=False, request=None):
    """Notify user when their group/role status changes (upgrade to Peer or other changes)"""
    try:
        settings = NotificationSettings.objects.get(user=user)
        if settings.account_deleted == NotificationChoices.NONE:
            return
    except NotificationSettings.DoesNotExist:
        pass

    email_settings = get_account_email_template_settings(request)

    if is_upgrade:
        greeting = email_settings["group_upgrade_greeting"]
        body = email_settings["group_upgrade_body"]
    else:
        greeting = email_settings["group_downgrade_greeting"]
        body = email_settings["group_downgrade_body"]

    context = {
        "user": user,
        "greeting": greeting,
        "body": body,
        "is_upgrade": is_upgrade,
        "site_url": request.build_absolute_uri("/") if request else "",
    }

    # Get email from settings
    try:
        settings = registry.get_by_natural_key("contact", "ContactEmailSettings").load(
            request
        )
        email_from = settings.default_sender
    except Exception:
        email_from = None
    # Send email
    try:
        email_body = render_to_string(
            "account/email/group_status_changed.html", context
        )
        send_mail(
            subject=_("Your Account Role Has Been Updated"),
            message=email_body,
            from_email=email_from,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=email_body,
        )
    except Exception:
        pass
