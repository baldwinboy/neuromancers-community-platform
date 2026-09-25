"""Admin help, tutorials and glossary content."""

from __future__ import annotations

from django import forms
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel
from wagtail.admin.panels import MultiFieldPanel
from wagtail.blocks import CharBlock
from wagtail.blocks import TextBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.search import index
from wagtail_daisIE.base_blocks import DaisieStreamBlock
from wagtail_daisIE.base_blocks import DaisieStructBlock
from wagtail_daisIE.blocks.content import ContentBlock

from .base import Timestamped


class HelpKind(models.TextChoices):
    REFERENCE = "reference", _("Reference")
    TUTORIAL = "tutorial", _("Tutorial")
    HOWTO = "howto", _("How-to")
    FAQ = "faq", _("FAQ")
    GLOSSARY = "glossary", _("Glossary")


class HelpAudience(models.TextChoices):
    ADMIN = "admin", _("Administrators")
    PEER = "peer", _("Care providers")
    SEEKER = "seeker", _("Care seekers")
    DEVELOPER = "developer", _("Developers")


class HelpDifficulty(models.TextChoices):
    EASY = "easy", _("Easy")
    MEDIUM = "medium", _("Medium")
    ADVANCED = "advanced", _("Advanced")


class HelpStepBlock(DaisieStructBlock):
    text = TextBlock(required=True)
    image = ImageChooserBlock(required=False)
    callout = CharBlock(required=False, label=_("Callout"))

    class Meta:
        icon = "list-ul"
        label = _("Step")


class HelpStepsBlock(DaisieStreamBlock):
    step = HelpStepBlock()


class HelpCategory(Timestamped):
    name = models.CharField(_("Name"), max_length=255, unique=True)
    slug = models.SlugField(_("Slug"), unique=True, blank=True)
    description = models.TextField(_("Description"), blank=True)
    icon = models.CharField(_("Icon"), max_length=64, blank=True)
    sort_order = models.PositiveIntegerField(_("Sort order"), default=0)
    is_active = models.BooleanField(_("Active"), default=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("icon"),
        FieldPanel("sort_order"),
        FieldPanel("is_active"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = _("Help category")
        verbose_name_plural = _("Help categories")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class HelpArticle(index.Indexed, Timestamped):
    title = models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True, blank=True)
    category = models.ForeignKey(
        HelpCategory,
        on_delete=models.PROTECT,
        related_name="articles",
        null=True,
        blank=True,
    )
    kind = models.CharField(
        _("Kind"),
        max_length=20,
        choices=HelpKind,
        default=HelpKind.REFERENCE,
    )
    summary = models.TextField(_("Summary"), blank=True)
    body = StreamField(
        ContentBlock(),
        blank=True,
        use_json_field=True,
        verbose_name=_("Body"),
    )
    steps = StreamField(
        HelpStepsBlock(),
        blank=True,
        use_json_field=True,
        verbose_name=_("Steps"),
    )
    screenshots = models.ManyToManyField(
        "wagtailimages.Image",
        blank=True,
        related_name="+",
    )
    video_url = models.URLField(_("Video URL"), blank=True)
    difficulty = models.CharField(
        _("Difficulty"),
        max_length=10,
        choices=HelpDifficulty,
        blank=True,
    )
    estimated_minutes = models.PositiveIntegerField(
        _("Estimated minutes"),
        null=True,
        blank=True,
    )
    audience = models.CharField(
        _("Audience"),
        max_length=20,
        choices=HelpAudience,
        blank=True,
    )
    related = models.ManyToManyField("self", blank=True, symmetrical=False)
    tags = TaggableManager(blank=True)
    is_published = models.BooleanField(_("Published"), default=False)
    sort_order = models.PositiveIntegerField(_("Sort order"), default=0)

    search_fields = [
        index.SearchField("title"),
        index.SearchField("summary"),
    ]

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("title"),
                FieldPanel("slug"),
                FieldPanel("category"),
                FieldPanel("kind"),
                FieldPanel("audience"),
                FieldPanel("summary"),
                FieldPanel("is_published"),
                FieldPanel("sort_order"),
            ],
            heading=_("Article"),
        ),
        FieldPanel("body"),
        FieldPanel("steps"),
        MultiFieldPanel(
            [
                FieldPanel("screenshots"),
                FieldPanel("video_url"),
                FieldPanel("difficulty"),
                FieldPanel("estimated_minutes"),
            ],
            heading=_("Media"),
        ),
        MultiFieldPanel(
            [FieldPanel("related"), FieldPanel("tags")],
            heading=_("Related"),
        ),
    ]

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name = _("Help article")
        verbose_name_plural = _("Help articles")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class GlossaryTerm(Timestamped):
    term = models.CharField(_("Term"), max_length=255, unique=True)
    definition = models.TextField(_("Definition"))
    aliases = models.CharField(
        _("Aliases"),
        max_length=255,
        blank=True,
        help_text=_("Comma-separated alternative names."),
    )
    related = models.ManyToManyField("self", blank=True, symmetrical=False)

    panels = [
        FieldPanel("term"),
        FieldPanel("definition"),
        FieldPanel("aliases"),
        FieldPanel("related"),
    ]

    class Meta:
        ordering = ["term"]
        verbose_name = _("Glossary term")
        verbose_name_plural = _("Glossary terms")

    def __str__(self):
        return self.term

    def get_aliases_list(self) -> list[str]:
        return [alias.strip() for alias in self.aliases.split(",") if alias.strip()]


class HelpFeedbackForm(forms.Form):
    """Simple helpfulness feedback attached to an article."""

    helpful = forms.BooleanField(required=False)
    comment = forms.CharField(required=False, widget=forms.Textarea)
