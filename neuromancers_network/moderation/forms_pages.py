"""Admin-authored support/report form page."""

from __future__ import annotations

import logging

from django.db import models
from modelcluster.fields import ParentalKey
from wagtail_daisIE.forms.fields import DaisieFormField
from wagtail_daisIE.forms.models import DaisieFormPage

logger = logging.getLogger(__name__)


class SupportFormField(DaisieFormField):
    page = ParentalKey(
        "moderation.SupportFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class SupportFormPage(DaisieFormPage):
    """A support/report form that creates a :class:`SupportTicket`."""

    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.core.audience import moderator_users  # noqa: PLC0415
        from neuromancers_network.inbox.events import emit  # noqa: PLC0415
        from neuromancers_network.moderation.models import SupportKind  # noqa: PLC0415
        from neuromancers_network.moderation.models import (  # noqa: PLC0415
            SupportTicket,
        )

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        data = form.cleaned_data
        ticket = SupportTicket.objects.create(
            kind=data.get("kind") or SupportKind.GENERAL,
            reporter=user if user is not None and user.is_authenticated else None,
            subject_url=data.get("subject_url", ""),
            message=data.get("message", ""),
        )
        try:
            emit(
                "report_created",
                payload={
                    "actor_user_id": getattr(user, "pk", None),
                    "recipient_user_ids": list(
                        moderator_users().values_list("pk", flat=True),
                    ),
                    "object_type": "supportticket",
                    "object_id": ticket.pk,
                    "meta": {"ticket_id": ticket.pk, "kind": ticket.kind},
                },
                event_ref=f"supportticket.{ticket.pk}.created",
            )
        except Exception:
            logger.exception("Failed to emit report_created for ticket %s", ticket.pk)
        return ticket
