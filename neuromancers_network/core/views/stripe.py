from __future__ import annotations

from uuid import uuid4

from django.contrib import messages
from django.core.management import call_command
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from djstripe.models.base import StripeBaseModel
from wagtail.admin.auth import require_admin_access
from wagtail.admin.ui.menus import MenuItem
from wagtail.admin.views.generic import IndexView

from neuromancers_network.core.forms import StripeWebhookForm
from neuromancers_network.core.models import StripeSettings
from neuromancers_network.payments.services import DEFAULT_WEBHOOK_EVENTS
from neuromancers_network.payments.services import create_webhook_endpoint


def stripe_model_names() -> list[str]:
    """Return the concrete dj-stripe model names available to sync."""
    names: set[str] = set()
    stack = list(StripeBaseModel.__subclasses__())
    while stack:
        model = stack.pop()
        stack.extend(model.__subclasses__())
        if not model._meta.abstract:  # noqa: SLF001
            names.add(model._meta.model_name)  # noqa: SLF001
    return sorted(names)


class ReadOnlyIndexView(IndexView):
    """A listing view with no add/edit/delete affordances (inspect only)."""

    def get_add_url(self):
        return None

    def get_edit_url(self, instance):
        return None

    def get_list_more_buttons(self, instance):
        buttons = []
        inspect_url = self.get_inspect_url(instance)
        if inspect_url:
            buttons.append(
                MenuItem(
                    _("Inspect"),
                    url=inspect_url,
                    icon_name="info-circle",
                    priority=10,
                ),
            )
        return buttons


@method_decorator(require_admin_access, name="dispatch")
class StripeSyncView(TemplateView):
    """Trigger a dj-stripe model sync from the Wagtail admin."""

    template_name = "wagtailadmin/stripe/sync.html"

    def dispatch(self, request, *args, **kwargs):
        if not StripeSettings.load(request).is_ready:
            return HttpResponseForbidden("Stripe is not configured")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stripe_models"] = stripe_model_names()
        return context

    def post(self, request, *args, **kwargs):
        selected = request.POST.getlist("models") or stripe_model_names()
        call_command("djstripe_sync_models", *selected)
        messages.success(request, "Stripe models synced.")
        return redirect(request.path)


@method_decorator(require_admin_access, name="dispatch")
class StripeWebhookView(FormView):
    """Create the platform Stripe webhook endpoint and store its secret."""

    template_name = "wagtailadmin/stripe/webhook.html"
    form_class = StripeWebhookForm

    def dispatch(self, request, *args, **kwargs):
        if not StripeSettings.load(request).is_ready:
            return HttpResponseForbidden("Stripe is not configured")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        webhook_uuid = uuid4()
        url = self.request.build_absolute_uri(
            reverse(
                "djstripe:djstripe_webhook_by_uuid",
                kwargs={"uuid": webhook_uuid},
            ),
        )
        return {
            "webhook_uuid": webhook_uuid,
            "url": url,
            "enabled_events": DEFAULT_WEBHOOK_EVENTS,
        }

    def form_valid(self, form):
        create_webhook_endpoint(
            url=form.cleaned_data["url"],
            enabled_events=form.cleaned_data["enabled_events"],
            djstripe_uuid=form.cleaned_data["webhook_uuid"],
        )
        messages.success(self.request, "Stripe webhook endpoint created.")
        return redirect(self.request.path)
