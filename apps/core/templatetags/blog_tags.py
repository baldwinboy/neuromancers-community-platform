"""
Template tags for blog-related functionality.
"""

from django import template

register = template.Library()


@register.simple_tag
def get_blog_posts(max_posts=10):
    """
    Get the latest blog posts.

    Usage:
        {% load blog_tags %}
        {% get_blog_posts max_posts=5 as posts %}
        {% for post in posts %}
            {{ post.title }}
        {% endfor %}
    """
    from apps.blog.models import BlogPage

    return BlogPage.objects.live().public().order_by("-date")[:max_posts]


@register.inclusion_tag("core/blocks/blog_feed_block.html", takes_context=True)
def render_blog_feed(context, block_value):
    """
    Render a blog feed with the given block configuration.

    Usage:
        {% load blog_tags %}
        {% render_blog_feed self %}
    """
    from apps.blog.models import BlogPage

    max_posts = block_value.get("max_posts", 10) if block_value else 10
    blog_posts = BlogPage.objects.live().public().order_by("-date")[:max_posts]

    return {
        "self": block_value,
        "blog_posts": blog_posts,
        "request": context.get("request"),
    }
