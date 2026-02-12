"""Template tag for rendering GetPronto-hosted images with optional transforms."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def pronto_img(url, alt="", w=None, h=None, q=None, fit=None, css_class="", **attrs):
    """Render an ``<img>`` tag pointing to a GetPronto image URL.

    Appends query-string transformation parameters when provided.

    Usage::

        {% load getpronto %}
        {% pronto_img user.profile.display_picture_url alt="Avatar" w=128 h=128 q=90 css_class="avatar" %}

    For raw URL output (no ``<img>`` tag) use the ``pronto_url`` tag instead.
    """
    if not url:
        return ""

    src = _build_url(url, w=w, h=h, q=q, fit=fit)
    extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items() if v)
    class_attr = f' class="{css_class}"' if css_class else ""
    loading = ' loading="lazy"'
    parts = [f'<img src="{src}" alt="{alt}"{class_attr}{loading}']
    if w:
        parts.append(f' width="{w}"')
    if h:
        parts.append(f' height="{h}"')
    if extra:
        parts.append(f" {extra}")
    parts.append(" />")
    return mark_safe("".join(parts))


@register.simple_tag
def pronto_url(url, w=None, h=None, q=None, fit=None):
    """Return a GetPronto image URL string with optional transform query params.

    Useful when you need the URL itself rather than a full ``<img>`` tag::

        {% load getpronto %}
        <div style="background-image: url('{% pronto_url img_url w=800 q=85 %}')">
    """
    if not url:
        return ""
    return _build_url(url, w=w, h=h, q=q, fit=fit)


def _build_url(base_url, **params):
    """Append non-None params as query string to *base_url*."""
    qs_parts = []
    for key, value in params.items():
        if value is not None:
            qs_parts.append(f"{key}={value}")
    if not qs_parts:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{'&'.join(qs_parts)}"
