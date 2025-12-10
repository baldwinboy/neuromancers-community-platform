from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, TemplateView, View

from apps.accounts.models_users.profile import StripeAccount
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


class UserSettingsView(LoginRequiredMixin, TemplateView):
    """
    View for logged-in users to manage their settings
    """

    template_name = "accounts/user_settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.has_perm("events.add_peersession"):
            try:
                stripe_account = StripeAccount.objects.get(user=self.request.user)
                context.update({"stripe_account": stripe_account})
            except StripeAccount.DoesNotExist:
                pass

        return context


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
