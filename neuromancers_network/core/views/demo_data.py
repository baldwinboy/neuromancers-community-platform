"""Superuser-only Wagtail admin view for demo/test data."""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import View
from wagtail.admin.auth import require_admin_access

from neuromancers_network.core.demo_data import DemoDataError
from neuromancers_network.core.demo_data import cleanup_demo_data
from neuromancers_network.core.demo_data import demo_data_status
from neuromancers_network.core.demo_data import seed_demo_data
from neuromancers_network.core.forms import DemoCleanupForm
from neuromancers_network.core.forms import DemoSeedForm


@method_decorator(require_admin_access, name="dispatch")
class DemoDataView(View):
    """Seed or clean demo data from the Wagtail dashboard."""

    template_name = "wagtailadmin/demo_data/index.html"

    def dispatch(self, request, *args, **kwargs):
        if not settings.DEMO_DATA_ENABLED:
            return HttpResponseForbidden("Demo data is disabled.")
        if not request.user.is_superuser:
            return HttpResponseForbidden("Only superusers can manage demo data.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.render_page(request)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "")
        if action == "seed":
            return self.seed(request)
        if action == "cleanup":
            return self.cleanup(request)
        messages.error(request, _("Unknown demo-data action."))
        return self.render_page(request)

    def seed(self, request):
        form = DemoSeedForm(request.POST)
        if not form.is_valid():
            return self.render_page(request, seed_form=form)
        try:
            result = seed_demo_data(
                email_base=form.cleaned_data["email_base"],
                password=form.cleaned_data["password"],
                actor=request.user,
                include_paused_peer=form.cleaned_data["include_paused_peer"],
            )
        except DemoDataError as exc:
            form.add_error(None, str(exc))
            return self.render_page(request, seed_form=form)
        messages.success(
            request,
            _("Demo data seeded: %(users)s users, %(meetings)s meetings.")
            % {
                "users": result["users"],
                "meetings": result["meetings"],
            },
        )
        return self.render_page(request)

    def cleanup(self, request):
        form = DemoCleanupForm(request.POST)
        if not form.is_valid():
            return self.render_page(request, cleanup_form=form)
        dry_run = form.cleaned_data["dry_run"]
        if not dry_run and form.cleaned_data["confirmation"] != "DELETE DEMO DATA":
            form.add_error(
                "confirmation",
                _("Type DELETE DEMO DATA to confirm a real cleanup."),
            )
            return self.render_page(request, cleanup_form=form)
        try:
            result = cleanup_demo_data(
                email_base=form.cleaned_data["email_base"],
                actor=request.user,
                dry_run=dry_run,
            )
        except DemoDataError as exc:
            form.add_error(None, str(exc))
            return self.render_page(request, cleanup_form=form)
        if dry_run:
            messages.info(request, _("Dry run only; nothing was deleted."))
        else:
            messages.success(request, _("Demo data cleaned up."))
        return self.render_page(
            request,
            cleanup_form=form,
            cleanup_result=result,
        )

    def render_page(
        self,
        request,
        *,
        seed_form=None,
        cleanup_form=None,
        cleanup_result=None,
    ):
        return render(
            request,
            self.template_name,
            {
                "seed_form": seed_form or DemoSeedForm(),
                "cleanup_form": cleanup_form or DemoCleanupForm(),
                "status": demo_data_status(),
                "cleanup_result": cleanup_result,
                "demo_enabled": settings.DEMO_DATA_ENABLED,
            },
        )
