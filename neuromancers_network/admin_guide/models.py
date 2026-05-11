from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import DraftStateMixin
from wagtail.models import LockableMixin
from wagtail.models import RevisionMixin
from wagtail import blocks


class GuideTopic(models.Model):
    title = models.CharField(max_length=255)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.title


class GuideTag(TaggedItemBase):
    content_object = ParentalKey(
        "admin_guide.Guide",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


class GuideParagraphBlock(blocks.StreamBlock):
    paragraph = blocks.RichTextBlock()

    class Meta:
        max_num = 1


class Guide(DraftStateMixin, LockableMixin, RevisionMixin, ClusterableModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    topic = models.ForeignKey(
        GuideTopic,
        related_name="guides",
        on_delete=models.CASCADE,
    )
    summary = models.TextField(blank=True)
    content = StreamField(
        GuideParagraphBlock(),
        use_json_field=True,
        blank=True,
    )
    tags = TaggableManager(
        through=GuideTag,
        blank=True,
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("slug"),
        FieldPanel("topic"),
        FieldPanel("summary"),
        FieldPanel("content"),
        FieldPanel("tags"),
    ]

    class Meta:
        ordering = ["title"]
        verbose_name = _("Admin Guide")
        verbose_name_plural = _("Admin Guides")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class OnboardingTask(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.title
