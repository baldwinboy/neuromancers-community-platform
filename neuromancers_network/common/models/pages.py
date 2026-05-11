from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.forms.models import AbstractEmailForm
from wagtail.contrib.forms.panels import FormSubmissionsPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from neuromancers_network.common.blocks import BackgroundStreamBlock
from neuromancers_network.common.blocks import ContentBlock
from neuromancers_network.common.blocks import ContentFormBlock


class StyledPageMixin(Page):
    """
    Optional per-page background overrides. If empty, the page inherits the
    site-wide backgrounds from SiteDesignSettings.
    """

    page_background = StreamField(
        BackgroundStreamBlock(),
        blank=True,
        use_json_field=True,
        help_text=_(
            "Add background blocks to override the site-wide design for this page.",
        ),
    )

    body = StreamField(
        ContentBlock(),
        blank=True,
        use_json_field=True,
        help_text=_("Add content blocks to build out the page body."),
    )

    class Meta:
        abstract = True

    content_panels = [
        *Page.content_panels,
        FieldPanel("page_background"),
        FieldPanel("body"),
    ]

    template = "common/base.html"


class StyledFormPageMixin(StyledPageMixin, AbstractEmailForm):
    """
    Extends StyledPageMixin with additional fields for form pages, like contact
    forms. This allows form pages to have the same optional background overrides
    and content blocks as regular pages, while also including form-specific fields.
    """

    body = StreamField(
        ContentFormBlock(),
        blank=True,
        use_json_field=True,
        help_text=_("Add content blocks to build out the page body."),
    )

    class Meta:
        abstract = True

    content_panels = [
        FormSubmissionsPanel(),
        *StyledPageMixin.content_panels,
    ]
