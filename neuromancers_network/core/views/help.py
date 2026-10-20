"""Staff-only reader for the admin help guide."""

from __future__ import annotations

from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from wagtail.admin.auth import require_admin_access
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from neuromancers_network.core.models import GlossaryTerm
from neuromancers_network.core.models import HelpArticle
from neuromancers_network.core.models import HelpCategory


@method_decorator(require_admin_access, name="dispatch")
class HelpGuideView(WagtailAdminTemplateMixin, TemplateView):
    """Render the seeded help categories, their articles and the glossary."""

    template_name = "core/help_guide.html"
    page_title = _("Admin Guide")
    header_icon = "help"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = HelpCategory.objects.filter(is_active=True).prefetch_related(
            Prefetch(
                "articles",
                queryset=HelpArticle.objects.filter(is_published=True),
            ),
        )
        context["help_groups"] = [
            {"category": category, "articles": category.articles.all()}
            for category in categories
        ]
        context["glossary_terms"] = GlossaryTerm.objects.all()
        return context
