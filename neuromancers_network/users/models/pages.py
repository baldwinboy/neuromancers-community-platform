import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from wagtail.contrib.routable_page.models import RoutablePageMixin
from wagtail.contrib.routable_page.models import route

from neuromancers_network.core.models import StyledPageMixin

logger = logging.getLogger(__name__)


class UserProfilePage(StyledPageMixin, RoutablePageMixin):
    """
    A singleton page for displaying user profiles. Uses `RoutablePageMixin` to
    define custom routes for profile viewing and editing. Inherits from
    `StyledPageMixin` to allow per-page design overrides.
    """

    page_description = _(
        "Use this page to customise the look of user profiles. All profiles will use the same design settings configured here.",
    )

    parent_page_types = ["core.HomePage"]
    subpage_types = []  # Prevent adding child pages under the profile page

    # Define routes for profile viewing and editing
    def get_context(self, request):
        context = super().get_context(request)
        return context  # noqa: RET504

    @route(r"")
    def profile_redirect(self, request):
        # Get current path to append users name to the URL
        current_path = request.path
        if request.user.is_authenticated:
            return redirect(f"{current_path}{request.user.username}/")
        return redirect("/login/")

    @route(r"(?P<username>[\w-]+)/$")
    def profile_view(self, request, username):
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return redirect("/404/")

        profile = user.profile
        settings = self.get_settings()

        return self.render(
            request,
            context_overrides={"profile": profile, "user_settings": settings},
            template="users/profile.html",
        )

    @route(r"^settings/$")
    def settings_dashboard(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        settings = self.get_settings()
        return self.render(
            request,
            context_overrides={"user_settings": settings},
            template="users/settings_dashboard.html",
        )

    @route(r"^settings/password/$")
    def settings_password(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        settings = self.get_settings()
        if not settings.enable_password_change:
            return redirect(f"{self.url}settings/")

        from django.contrib.auth.forms import PasswordChangeForm

        form = PasswordChangeForm(user=request.user)
        if request.method == "POST":
            form = PasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)
                messages.success(request, _("Your password was successfully updated."))
                return redirect(f"{self.url}settings/")
            messages.error(request, _("Please correct the errors below."))

        return self.render(
            request,
            context_overrides={"form": form, "user_settings": settings},
            template="users/settings_password.html",
        )

    @route(r"^settings/email/$")
    def settings_email(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        settings = self.get_settings()
        if not settings.enable_email_management:
            return redirect(f"{self.url}settings/")

        if request.method == "POST":
            from allauth.account.views import EmailView

            return EmailView.as_view()(request)

        return self.render(
            request,
            context_overrides={"user_settings": settings},
            template="users/settings_email.html",
        )

    @route(r"^settings/notifications/$")
    def settings_notifications(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        settings = self.get_settings()
        if not settings.enable_notification_prefs:
            return redirect(f"{self.url}settings/")

        profile = request.user.profile
        if request.method == "POST":
            prefs = {}
            for key in request.POST:
                if key.startswith("notify_"):
                    prefs[key] = request.POST.get(key) == "on"
            profile.notification_prefs = prefs
            profile.save(update_fields=["notification_prefs"])
            messages.success(request, _("Notification preferences updated."))
            return redirect(f"{self.url}settings/")

        return self.render(
            request,
            context_overrides={
                "profile": profile,
                "user_settings": settings,
            },
            template="users/settings_notifications.html",
        )

    @route(r"^settings/profile/$")
    def settings_profile(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        settings = self.get_settings()
        if not settings.enable_profile_edit:
            return redirect(f"{self.url}settings/")

        if request.method == "POST":
            name = request.POST.get("name", "").strip()
            bio = request.POST.get("bio", "").strip()
            if name:
                request.user.name = name
                request.user.save(update_fields=["name"])
            if hasattr(request.user, "profile"):
                request.user.profile.bio = bio
                request.user.profile.save(update_fields=["bio"])
            messages.success(request, _("Profile updated."))
            return redirect(f"{self.url}settings/")

        return self.render(
            request,
            context_overrides={"user_settings": settings},
            template="users/settings_profile.html",
        )
