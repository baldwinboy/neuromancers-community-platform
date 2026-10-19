# ruff: noqa: PLC0415
"""Admin-authored support/report form page."""

from __future__ import annotations

import logging

from django.db import models
from modelcluster.fields import ParentalKey
from wagtail_daisIE.forms.fields import DaisieFormField

from neuromancers_network.core.forms_pages import ProjectDaisieFormPage

logger = logging.getLogger(__name__)

_SUPPORT_TICKET_FIELDS = {"kind", "subject_url", "message", "subject_user"}


def _resolve_subject_user(value):
    if value is None or value == "":
        return None
    from neuromancers_network.users.models import User

    if isinstance(value, User):
        return value
    user = None
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        user = User.objects.filter(pk=value).first()
    if user is None and isinstance(value, str):
        user = User.objects.filter(username__iexact=value.strip()).first()
    return user


class SupportFormField(DaisieFormField):
    page = ParentalKey(
        "moderation.SupportFormPage",
        on_delete=models.CASCADE,
        related_name="form_fields",
    )


class SupportFormPage(ProjectDaisieFormPage):
    """A support/report form that creates a :class:`SupportTicket`."""

    template = "wagtail_daisIE/forms/form_page.html"
    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []

    def create_instance_from_submission(self, form, submission=None):
        from neuromancers_network.core.audience import moderator_users
        from neuromancers_network.inbox.events import emit
        from neuromancers_network.moderation.models import SupportKind
        from neuromancers_network.moderation.models import SupportTicket

        request = getattr(self, "_daisie_request", None)
        user = getattr(request, "user", None)
        mapping = self.get_model_field_map()

        kwargs = {}
        subject_user = None
        for name, value in form.cleaned_data.items():
            target = mapping.get(name, name)
            if target not in _SUPPORT_TICKET_FIELDS:
                continue
            if target == "subject_user":
                subject_user = _resolve_subject_user(value)
            else:
                kwargs[target] = value

        kind = kwargs.get("kind") or SupportKind.GENERAL
        if kind not in SupportKind.values:
            kind = SupportKind.GENERAL
        kwargs["kind"] = kind

        ticket = SupportTicket.objects.create(
            reporter=user if user is not None and user.is_authenticated else None,
            subject_user=subject_user,
            **kwargs,
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
