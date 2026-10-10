"""Admin views for the taxonomy app."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from wagtail.admin.auth import require_admin_access

from neuromancers_network.taxonomy import registry
from neuromancers_network.taxonomy.models import Country
from neuromancers_network.taxonomy.models import Language


@method_decorator(require_admin_access, name="dispatch")
class LoadRegistryView(TemplateView):
    """Confirm and run a registry import for a single taxonomy model."""

    template_name = "wagtailadmin/taxonomy/load_registry.html"
    model = None
    index_url_name = ""

    def _load(self) -> tuple[int, int, int]:
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model_name"] = self.model._meta.verbose_name_plural  # noqa: SLF001
        return context

    def post(self, request, *args, **kwargs):
        created, updated, skipped = self._load()
        messages.success(
            request,
            _(
                "Registry import complete: %(created)d created, "
                "%(updated)d updated, %(skipped)d skipped.",
            )
            % {"created": created, "updated": updated, "skipped": skipped},
        )
        return redirect(reverse(self.index_url_name))


class LoadCountriesView(LoadRegistryView):
    model = Country
    index_url_name = "wagtailsnippets_taxonomy_country:list"

    def _load(self) -> tuple[int, int, int]:
        return registry.load_countries()


class LoadLanguagesView(LoadRegistryView):
    model = Language
    index_url_name = "wagtailsnippets_taxonomy_language:list"

    def _load(self) -> tuple[int, int, int]:
        return registry.load_languages()
