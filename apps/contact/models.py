from django import forms
from django.db import models
from django.utils.text import slugify
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.fields import RichTextField
from wagtail.snippets.models import register_snippet


@register_snippet
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
class ContactFormSettings(BaseGenericSetting):
    default_recipient = models.EmailField(
        help_text="Email address to receive Contact Form submissions"
    )

    panels = [
        FieldPanel("default_recipient"),
    ]


class ContactFormField(AbstractFormField):
    page = ParentalKey(
        "ContactFormPage", on_delete=models.CASCADE, related_name="form_fields"
    )


class ContactFormPage(AbstractEmailForm):
    intro = RichTextField(blank=True)
    thank_you_text = RichTextField(blank=True)

    content_panels = AbstractEmailForm.content_panels + [
        FieldPanel("intro"),
        InlinePanel("form_fields", label="Form fields"),
        FieldPanel("thank_you_text"),
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
        settings = ContactFormSettings.load(self._request)
        return [settings.default_recipient]

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
