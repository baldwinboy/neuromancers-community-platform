from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView, View

from apps.accounts.forms import (
    NotificationSettingsForm,
    PeerNotificationSettingsForm,
    ProfileForm,
)
from apps.accounts.models_users.profile import StripeAccount
from apps.accounts.models_users.user_settings import (
    Notifications,
    NotificationSettings,
    PeerNotificationSettings,
)
from apps.common.utils import (
    get_stripe_oauth,
    get_stripe_oauth_url,
    is_stripe_account_ready,
)

User = get_user_model()


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    View for logged-in users to see their own profile
    """

    template_name = "accounts/profile.html"


class UserView(DetailView):
    """
    View for any user to see other profiles
    """

    model = User
    context_object_name = "other_user"
    template_name = "accounts/user_profile.html"
    pk_url_kwarg = "username"

    def get_object(self):
        return get_object_or_404(
            self.model, username=self.kwargs.get(self.pk_url_kwarg)
        )

    def get(self, request, *args, **kwargs):
        """
        Redirect logged-in users querying their own profile to ProfileView
        """
        username = self.kwargs.get(self.pk_url_kwarg)
        if request.user.is_authenticated and request.user.username == username:
            return redirect("accounts_profile")

        return super().get(self, request, *args, **kwargs)


class UserSettingsView(LoginRequiredMixin, FormView):
    """
    View for logged-in users to manage their settings with tabbed interface
    """

    template_name = "accounts/user_settings.html"
    form_class = ProfileForm  # Default tab

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user.profile
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Determine active tab from query parameter
        active_tab = self.request.GET.get("tab", "profile")
        context["active_tab"] = active_tab

        # Profile form (always available)
        if "profile_form" not in context:
            context["profile_form"] = ProfileForm(
                instance=self.request.user.profile,
                user=self.request.user,
                prefix="profile",
            )

        # Notification forms
        if "notification_form" not in context:
            notification_settings, _ = NotificationSettings.objects.get_or_create(
                user=self.request.user
            )
            context["notification_form"] = NotificationSettingsForm(
                instance=notification_settings,
                prefix="notifications",
            )

        # Peer-specific notification form
        if self.request.user.has_perm("events.add_peersession"):
            if "peer_notification_form" not in context:
                peer_settings, _ = PeerNotificationSettings.objects.get_or_create(
                    user=self.request.user
                )
                context["peer_notification_form"] = PeerNotificationSettingsForm(
                    instance=peer_settings,
                    prefix="peer_notifications",
                )

        # Stripe account info
        if self.request.user.has_perm("events.add_peersession"):
            try:
                stripe_account = StripeAccount.objects.get(user=self.request.user)
                context["stripe_account"] = stripe_account
            except StripeAccount.DoesNotExist:
                context["stripe_account"] = None

        return context

    def post(self, request, *args, **kwargs):
        """Handle form submissions based on which form was submitted"""
        form_type = request.POST.get("form_type")

        if form_type == "profile":
            form = ProfileForm(
                request.POST,
                request.FILES,
                instance=request.user.profile,
                user=request.user,
                prefix="profile",
            )
            if form.is_valid():
                profile = form.save(commit=False)
                profile.has_customized = True
                profile.save()
                messages.success(request, "Profile updated successfully")
                return redirect(f"{reverse('accounts_user_settings')}?tab=profile")
            else:
                return self.form_invalid_with_context(form, "profile_form", "profile")

        elif form_type == "notifications":
            notification_settings, _ = NotificationSettings.objects.get_or_create(
                user=request.user
            )
            form = NotificationSettingsForm(
                request.POST,
                instance=notification_settings,
                prefix="notifications",
            )
            if form.is_valid():
                settings = form.save(commit=False)
                settings.has_customized = True
                settings.save()
                messages.success(request, "Notification settings updated successfully")
                return redirect(
                    f"{reverse('accounts_user_settings')}?tab=notifications"
                )
            else:
                return self.form_invalid_with_context(
                    form, "notification_form", "notifications"
                )

        elif form_type == "peer_notifications":
            if not request.user.has_perm("events.add_peersession"):
                messages.error(
                    request, "You don't have permission to update these settings"
                )
                return redirect(reverse("accounts_user_settings"))

            peer_settings, _ = PeerNotificationSettings.objects.get_or_create(
                user=request.user
            )
            form = PeerNotificationSettingsForm(
                request.POST,
                instance=peer_settings,
                prefix="peer_notifications",
            )
            if form.is_valid():
                settings = form.save(commit=False)
                settings.has_customized = True
                settings.save()
                messages.success(
                    request, "Host notification settings updated successfully"
                )
                return redirect(
                    f"{reverse('accounts_user_settings')}?tab=notifications"
                )
            else:
                return self.form_invalid_with_context(
                    form, "peer_notification_form", "notifications"
                )

        return redirect(reverse("accounts_user_settings"))

    def form_invalid_with_context(self, form, form_key, tab):
        """Helper to render form with errors in correct tab"""
        context = self.get_context_data()
        context[form_key] = form
        context["active_tab"] = tab
        return self.render_to_response(context)


class StripeAuthorizeView(LoginRequiredMixin, View):
    def get(self, request):
        if not request.user.has_perm("events.add_peersession"):
            return redirect(reverse("accounts_user_settings"))

        return redirect(get_stripe_oauth_url(request))


class StripeAuthorizeCallbackView(LoginRequiredMixin, View):
    def get(self, request):
        next = reverse("accounts_user_settings")

        if not request.user.has_perm("events.add_peersession"):
            return redirect(next)

        code = request.GET.get("code")
        if code:
            try:
                response = get_stripe_oauth(code=code, request=request)
                if response["stripe_user_id"]:
                    account_id = response["stripe_user_id"]

                    is_ready = is_stripe_account_ready(account_id, request=request)

                    stripe_account, created = StripeAccount.objects.get_or_create(
                        user=request.user,
                        defaults={
                            "is_ready": is_ready,
                            "id": response["stripe_user_id"],
                        },
                    )

                    if not created:
                        stripe_account.id = response["stripe_user_id"]
                        stripe_account.is_ready = is_ready
                        stripe_account.save()
            except:  # noqa: E722
                pass

        return redirect(next)


class StripeDisconnectView(LoginRequiredMixin, View):
    """Disconnect user's Stripe account"""

    def post(self, request):
        if not request.user.has_perm("events.add_peersession"):
            messages.error(request, "You don't have permission to disconnect Stripe")
            return redirect(reverse("accounts_user_settings"))

        try:
            StripeAccount.objects.filter(user=request.user).delete()
            messages.success(request, "Stripe account disconnected successfully")
        except Exception as e:
            messages.error(request, f"Error disconnecting Stripe: {str(e)}")

        return redirect(f"{reverse('accounts_user_settings')}?tab=stripe")


class NotificationInboxView(LoginRequiredMixin, TemplateView):
    """
    Display user's notifications in an inbox-style interface.
    """

    template_name = "accounts/notification_inbox.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's notifications, ordered by newest first
        notifications = Notifications.objects.filter(
            sent_to=self.request.user
        ).order_by("-sent_at")

        # Paginate
        paginator = Paginator(notifications, 20)  # 20 per page
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["notifications"] = page_obj.object_list
        context["unread_count"] = notifications.filter(read=False).count()

        return context


class MarkNotificationReadView(LoginRequiredMixin, TemplateView):
    """
    AJAX endpoint to mark a notification as read.
    """

    def post(self, request, notification_id):
        notification = get_object_or_404(
            Notifications, id=notification_id, sent_to=request.user
        )
        notification.read = True
        notification.save(update_fields=["read"])

        return JsonResponse({"success": True})


class MarkAllNotificationsReadView(LoginRequiredMixin, TemplateView):
    """
    AJAX endpoint to mark all notifications as read.
    """

    def post(self, request):
        Notifications.objects.filter(sent_to=request.user, read=False).update(read=True)
        return JsonResponse({"success": True})


class ClearNotificationsView(LoginRequiredMixin, TemplateView):
    """
    Delete all read notifications.
    """

    def post(self, request):
        Notifications.objects.filter(sent_to=request.user, read=True).delete()
        return JsonResponse({"success": True})
