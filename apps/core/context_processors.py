from allauth.account.models import EmailAddress
from django.contrib import messages


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
            messages.add_message(request, messages.INFO, "Review your profile")

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
                request, messages.INFO, "Review your notification preferences"
            )

            return {}

    return {}
