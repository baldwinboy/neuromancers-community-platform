from allauth.account.models import EmailAddress
from django.contrib import messages


def unverified_email_warning(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return {}

        # Skip admin pages
        if request.path.startswith("/admin/"):
            return {}

        email_verified = EmailAddress.objects.filter(
            user=request.user, primary=True, verified=True
        ).exists()

        if not email_verified:
            storage = messages.get_messages(request)

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
                    f"Verify your account by clicking the link sent to {request.user.email}",
                )

    return {}
