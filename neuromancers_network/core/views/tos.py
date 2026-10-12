"""Staff-only controls for resetting Terms acceptance across audiences."""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import ngettext
from django.views.generic import FormView
from wagtail.admin.auth import require_admin_access

from neuromancers_network.core.forms import ResetTosForm
from neuromancers_network.core.utils import users_for_audiences


@method_decorator(require_admin_access, name="dispatch")
class ResetTosView(FormView):
    """Reset ``accepted_tos`` for every member in the chosen audiences."""

    template_name = "wagtailadmin/tos/reset.html"
    form_class = ResetTosForm

    def form_valid(self, form):
        base = users_for_audiences(form.cleaned_data["audiences"])
        updated = base.filter(accepted_tos=True).update(accepted_tos=False)

        messages.success(
            self.request,
            ngettext(
                "%(num)d member must accept the Terms again.",
                "%(num)d members must accept the Terms again.",
                updated,
            )
            % {"num": updated},
        )
        return HttpResponseRedirect(reverse("wagtailadmin_home"))
