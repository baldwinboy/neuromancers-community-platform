from django import forms
from django.db import models
from django.utils.text import slugify
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.fields import RichTextField, StreamField

from apps.core.models import get_shared_streamfield_blocks


class ContactTopic(models.Model):
    label = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)

    panels = [
        FieldPanel("label"),
        FieldPanel("slug"),
    ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.label)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label


@register_setting(icon="mail")
class ContactEmailSettings(BaseGenericSetting):
    default_recipient = models.EmailField(
        help_text=(
            "Email address to receive contact form submissions. "
            "If you'd like to include a name for the recipient, "
            "include the name before the email address like so: "
            "Your Name <email@example.com>"
        ),
        null=True,
        blank=True,
    )
    default_sender = models.EmailField(
        help_text=(
            "Email address to send communication to users. "
            "If you'd like to include a name for the recipient, "
            "include the name before the email address like so: "
            "Your Name <email@example.com>"
        ),
        null=True,
        blank=True,
    )

    panels = [
        FieldPanel("default_recipient"),
        FieldPanel("default_sender"),
    ]


class ContactFormField(AbstractFormField):
    page = ParentalKey(
        "ContactFormPage", on_delete=models.CASCADE, related_name="form_fields"
    )


class ContactFormPage(AbstractEmailForm):
    """
    Contact form page with StreamField content above the form.
    """

    # StreamField for flexible content above the form
    body = StreamField(
        get_shared_streamfield_blocks(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Optional content blocks above the contact form",
    )

    intro = RichTextField(blank=True, help_text="Text displayed above the form")
    thank_you_text = RichTextField(
        blank=True, help_text="Text displayed after form submission"
    )

    content_panels = AbstractEmailForm.content_panels + [
        FieldPanel("body"),
        MultiFieldPanel(
            [
                FieldPanel("intro"),
                InlinePanel("form_fields", label="Form fields"),
                FieldPanel("thank_you_text"),
            ],
            heading="Form Settings",
        ),
    ]

    parent_page_types = ["core.HomePage"]

    def serve(self, request):
        self._request = request
        return super().serve(request)

    def get_initial(self, request):
        initial = super().get_initial(request)
        if request.user.is_authenticated:
            initial["account_username"] = request.user.username
            initial["contact_email"] = request.user.email
        return initial

    def get_to_address(self):
        settings = ContactEmailSettings.load(self._request)
        if settings.default_recipient:
            return [settings.default_recipient]
        return []

    def get_from_address(self):
        settings = ContactEmailSettings.load(self._request)
        return settings.default_sender or ""

    def get_subject(self, form):
        # Topic: use the label of the submitted choice
        topic_value = form.cleaned_data.get("topic", "")
        topic_label = topic_value  # fallback
        try:
            topic_obj = ContactTopic.objects.filter(slug=topic_value).first()
            if topic_obj:
                topic_label = topic_obj.label
        except ImportError:
            pass

        # User info
        request = getattr(self, "_request", None)
        if request and request.user.is_authenticated:
            username = request.user.get_username()
        else:
            username = form.cleaned_data.get("contact_email", "Unknown User")

        return f"[{topic_label}] Query from {username}"

    def send_mail(self, form):
        """Override to use settings from ContactEmailSettings."""
        from django.core.mail import send_mail

        addresses = self.get_to_address()
        if not addresses or not addresses[0]:
            return  # No recipient configured, skip sending

        from_address = self.get_from_address()
        subject = self.get_subject(form)
        content = self.render_email(form)

        send_mail(
            subject,
            content,
            from_address,
            addresses,
            fail_silently=True,
        )
