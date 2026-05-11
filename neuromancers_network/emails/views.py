from __future__ import annotations

import logging

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.admin.views.generic import InspectView
from wagtail.admin.viewsets.model import ModelViewSet

from neuromancers_network.emails.models import EmailTemplate
from neuromancers_network.emails.utils import render_email_template

logger = logging.getLogger(__name__)


class EmailTemplateViewSet(ModelViewSet):
    model = EmailTemplate

    icon = "mail"

    menu_label = _("Email Templates")

    menu_name = "email_templates"

    add_to_admin_menu = True

    inspect_view_enabled = True

    list_display = [
        "name",
        "event_type",
        "subject",
        "is_active",
    ]

    list_filter = [
        "event_type",
        "is_active",
    ]

    search_fields = [
        "name",
        "subject",
    ]

    ordering = ["name"]

    panels = [
        FieldPanel("name"),
        FieldPanel("event_type"),
        FieldPanel("subject"),
        FieldPanel("body"),
        FieldPanel("is_active"),
    ]

    def get_inspect_view(self):
        class EmailTemplateInspectView(InspectView):
            def get_fields_dict(self):
                obj = self.object
                return {
                    "name": obj.name,
                    "event_type": obj.get_event_type_display(),
                    "subject": obj.subject,
                    "is_active": obj.is_active,
                }

            def get_context_data(self, **kwargs):
                context = super().get_context_data(**kwargs)
                html = None
                try:
                    result = render_email_template(self.object.name)
                    if result:
                        html = result[1]
                except Exception:
                    logger.exception("Preview failed for template %s", self.object.name)
                context["email_html"] = html
                return context

            template_name = "emails/admin/inspect.html"

        return EmailTemplateInspectView

    def get_inspect_url(self):
        return lambda instance: reverse(
            "email_templates_inspect",
            kwargs={"pk": instance.pk},
        )
