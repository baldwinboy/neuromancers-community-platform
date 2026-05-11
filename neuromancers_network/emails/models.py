import logging

from django.db import models
from django.template.loader import render_to_string
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import PreviewableMixin

logger = logging.getLogger(__name__)


class EmailTemplateBlock(blocks.StreamBlock):
    heading = blocks.CharBlock()
    paragraph = blocks.RichTextBlock()
    button = blocks.StructBlock(
        [
            ("text", blocks.CharBlock()),
            ("url", blocks.CharBlock()),
        ]
    )
    divider = blocks.StructBlock([])
    image = ImageChooserBlock()
    spacer = blocks.IntegerBlock(default=20, help_text="px")


class EmailTemplate(PreviewableMixin, models.Model):
    """Admin-editable email via Wagtail blocks → MJML rendering."""

    name = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(
        max_length=50,
        choices=[
            ("account_created", "Account Created"),
            ("session_booked", "Session Booked"),
            ("session_reminder", "Session Reminder"),
            ("payment_received", "Payment Received"),
            ("login_code", "Login Code"),
            ("email_verification", "Email Verification"),
            ("password_reset", "Password Reset"),
            ("email_confirmation", "Email Confirmation"),
        ],
    )
    subject = models.CharField(max_length=255)
    body = StreamField(EmailTemplateBlock(), use_json_field=True)
    is_active = models.BooleanField(default=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("event_type"),
        FieldPanel("subject"),
        FieldPanel("body"),
        FieldPanel("is_active"),
    ]

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.name}"

    def get_preview_template(self, request, mode_name):
        return "emails/admin/preview.html"

    def get_preview_context(self, request, mode_name):
        html = None
        try:
            from neuromancers_network.emails.utils import render_email_template
            result = render_email_template(self.name)
            if result:
                html = result[1]
        except Exception:
            logger.exception("Preview failed for template %s", self.name)
        return {"email_html": html, "template_obj": self}

    def render_to_mjml(self, context=None):
        """Walk StreamField blocks, produce MJML markup, render via MJML API."""
        mjml = [
            "<mjml><mj-body>",
            *[self._block_to_mjml(block) for block in self.body],
            "</mj-body></mjml>",
        ]
        return "\n".join(mjml)

    def _block_to_mjml(self, block):
        """Convert a single StreamField block into MJML markup."""
        from wagtail.images.models import Image

        block_type = block.get("type")
        value = block.get("value")

        if block_type == "heading":
            return f"<mj-text font-size='20px' font-weight='bold'>{value}</mj-text>"
        elif block_type == "paragraph":
            return f"<mj-text>{value}</mj-text>"
        elif block_type == "button":
            return (
                f"<mj-button href='{value['url']}'>{value['text']}</mj-button>"
            )
        elif block_type == "divider":
            return "<mj-divider />"
        elif block_type == "image":
            if isinstance(value, Image):
                return f"<mj-image src='{value.url}' />"
            return "<mj-image src='' />"
        elif block_type == "spacer":
            return f"<mj-spacer height='{value}px' />"
        return ""
