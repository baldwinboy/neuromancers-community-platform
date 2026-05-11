from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from neuromancers_network.common.mjml import MJMLClient
from neuromancers_network.emails.models import EmailTemplate

logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    success: bool
    recipient: str
    template_name: str
    error: str | None = None


def render_email_template(
    template_name: str,
    context: dict[str, Any] | None = None,
) -> tuple[str, str] | None:
    """
    Render an EmailTemplate to (subject, html_body).

    Returns None if template is not found or not active.
    """
    try:
        tmpl = EmailTemplate.objects.get(name=template_name, is_active=True)
    except EmailTemplate.DoesNotExist:
        logger.warning("Email template '%s' not found or inactive", template_name)
        return None

    subject = tmpl.subject
    mjml_content = tmpl.render_to_mjml()

    mjml_wrapped = render_to_string(
        "emails/layout.mjml",
        {"content": mjml_content, **(context or {})},
    )

    try:
        external_api_settings = __import__(
            "neuromancers_network.core.models.settings",
            from_list=["ExternalAPISettings"],
        ).ExternalAPISettings.load()
        client = MJMLClient(
            application_id=external_api_settings.mjml_application_id,
            secret_key=external_api_settings.mjml_secret_key,
        )
        result = client.render_to_html(mjml_wrapped)
    except Exception:
        logger.exception("MJML rendering failed for template '%s'", template_name)
        return None

    return subject, result


def send_db_email(
    to: list[str],
    template_name: str,
    context: dict[str, Any] | None = None,
    from_email: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> EmailResult:
    """
    Send an email using a database-managed EmailTemplate.

    Looks up the template by name, renders it through MJML, and sends
    via Django's email backend.
    """
    rendered = render_email_template(template_name, context)
    if rendered is None:
        for recipient in to:
            logger.error("Failed to render email '%s' for %s", template_name, recipient)
        return EmailResult(
            success=False,
            recipient=", ".join(to),
            template_name=template_name,
            error="Template not found or rendering failed",
        )

    subject, html_body = rendered
    text_body = strip_tags(html_body)

    from_email = from_email or settings.DEFAULT_FROM_EMAIL

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=to,
        cc=cc or [],
        bcc=bcc or [],
    )
    message.attach_alternative(html_body, "text/html")

    try:
        message.send(fail_silently=False)
        for recipient in to:
            logger.info("Sent email '%s' to %s", template_name, recipient)
        return EmailResult(
            success=True,
            recipient=", ".join(to),
            template_name=template_name,
        )
    except Exception as e:
        for recipient in to:
            logger.exception("Failed to send email '%s' to %s: %s", template_name, recipient, e)
        return EmailResult(
            success=False,
            recipient=", ".join(to),
            template_name=template_name,
            error=str(e),
        )
