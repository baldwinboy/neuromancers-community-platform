from allauth.account.models import EmailAddress
from django.contrib import messages
from wagtail.models import Site

from apps.accounts.models_users.user_settings import Notifications


def unread_notification_count(request):
    if request.user.is_authenticated:
        count = Notifications.objects.filter(sent_to=request.user, read=False).count()
        return {"unread_notification_count": count}
    return {"unread_notification_count": 0}


def web_design_settings(request):
    """
    Add web design settings to the template context.
    Makes fonts, colors, logo, and other design settings available globally.
    """
    from apps.core.models import (
        DashboardPageContent,
        NavigationSettings,
        NotificationsPageContent,
        ProfilePageContent,
        SessionDetailPageContent,
        WebDesignSettings,
    )

    try:
        site = Site.find_for_request(request)
        settings = WebDesignSettings.load(request_or_site=site)
        nav_settings = NavigationSettings.load(request_or_site=site)
        profile_content = ProfilePageContent.load(request_or_site=site)
        dashboard_content = DashboardPageContent.load(request_or_site=site)
        notifications_content = NotificationsPageContent.load(request_or_site=site)
        session_detail_content = SessionDetailPageContent.load(request_or_site=site)

        return {
            "web_design": settings,
            "font_links": settings.get_font_links() if settings else [],
            "color_map": settings.get_color_map() if settings else {},
            "color_choices": settings.get_color_choices() if settings else [],
            "font_choices": settings.get_font_choices() if settings else [],
            "nav_settings": nav_settings,
            "profile_content": profile_content,
            "dashboard_content": dashboard_content,
            "notifications_content": notifications_content,
            "session_detail_content": session_detail_content,
        }
    except Exception:
        return {
            "web_design": None,
            "font_links": [],
            "color_map": {},
            "color_choices": [],
            "font_choices": [],
            "nav_settings": None,
            "profile_content": None,
            "dashboard_content": None,
            "notifications_content": None,
            "session_detail_content": None,
        }


def onboarding_banner(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return {}

        # Skip admin pages
        if request.path.startswith("/admin/"):
            return {}

        storage = messages.get_messages(request)

        email_verified = EmailAddress.objects.filter(
            user=request.user, primary=True, verified=True
        ).exists()

        if not email_verified:
            if isinstance(storage, list) and storage:
                return {}

            if not any(
                msg.message.startswith(
                    "Verify your account by clicking the link sent to"
                )
                for msg in list(storage)
            ):
                messages.add_message(
                    request,
                    messages.INFO,
                    (
                        "Verify your account by clicking the link sent to ",
                        request.user.email,
                    ),
                )

            return {}

        if not request.user.profile.has_customized and not any(
            msg.message.startswith("Review your profile") for msg in list(storage)
        ):
            messages.add_message(
                request,
                messages.INFO,
                "Review your profile",
                extra_tags="accounts_user_settings",
            )

            return {}

        notification_settings = (
            request.user.peer_notification_settings
            if request.user.has_perm("add_peersession")
            else request.user.notification_settings
        )

        if not notification_settings.has_customized and not any(
            msg.message.startswith("Review your notification preferences")
            for msg in list(storage)
        ):
            messages.add_message(
                request,
                messages.INFO,
                "Review your notification preferences",
                extra_tags="accounts_user_settings",
            )

            return {}

    return {}
