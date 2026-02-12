from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page

from apps.core.models import get_shared_streamfield_blocks


class BlogIndexPage(Page):
    """
    Blog index page that lists child blog posts.
    Includes a StreamField body for flexible content above the blog listing.
    """

    intro = RichTextField(blank=True)

    body = StreamField(
        get_shared_streamfield_blocks(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Optional content blocks above the blog listing",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    subpage_types = ["blog.BlogPage"]
    parent_page_types = ["core.HomePage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # Get child blog pages, ordered by date descending
        blog_posts = BlogPage.objects.child_of(self).live().public().order_by("-date")
        context["blog_posts"] = blog_posts
        return context


class BlogPage(Page):
    date = models.DateField("Post date")
    intro = models.CharField(max_length=250)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("date"),
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    parent_page_types = ["blog.BlogIndexPage"]
