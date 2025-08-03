from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, TemplateView

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
