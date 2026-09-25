"""Admin view to send a test email through the configured SMTP backend."""

from __future__ import annotations

from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from wagtail.admin.auth import require_admin_access

from neuromancers_network.core.forms import SendTestEmailForm


class SendTestEmailView(FormView):
    """Send a test email to a recipient supplied by the admin."""

    template_name = "wagtailadmin/email/send_test.html"
    form_class = SendTestEmailForm

    @require_admin_access
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        send_mail(
            subject=_("NEUROMANCERS test email"),
            message=_("This is a test email from the NEUROMANCERS admin."),
            from_email=None,
            recipient_list=[form.cleaned_data["email"]],
            fail_silently=False,
        )
        messages.success(self.request, _("Test email sent."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("wagtailadmin_home")
