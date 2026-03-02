"""Template tag for rendering ImageKit-hosted images with optional transforms.

Note: This file is named getpronto.py for backwards compatibility with existing
templates. The tags work with any image URL that supports query-string transforms,
including ImageKit URLs.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def pronto_img(url, alt="", w=None, h=None, q=None, fit=None, css_class="", **attrs):
    """Render an ``<img>`` tag pointing to an image URL with transforms.

    Appends query-string transformation parameters when provided.
    Works with ImageKit URLs using their transformation syntax.

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
    """Return an image URL string with optional transform query params.

    Works with ImageKit URLs using their transformation syntax.

    Useful when you need the URL itself rather than a full ``<img>`` tag::

        {% load getpronto %}
        <div style="background-image: url('{% pronto_url img_url w=800 q=85 %}')">
    """
    if not url:
        return ""
    return _build_url(url, w=w, h=h, q=q, fit=fit)


# ImageKit-compatible aliases
@register.simple_tag
def imagekit_img(url, alt="", w=None, h=None, q=None, fit=None, css_class="", **attrs):
    """Alias for pronto_img - renders an <img> tag with ImageKit transforms."""
    return pronto_img(
        url, alt=alt, w=w, h=h, q=q, fit=fit, css_class=css_class, **attrs
    )


@register.simple_tag
def imagekit_url(url, w=None, h=None, q=None, fit=None):
    """Alias for pronto_url - returns an ImageKit URL with transforms."""
    return pronto_url(url, w=w, h=h, q=q, fit=fit)


def _build_url(base_url, **params):
    """Append non-None params as ImageKit transformation query string.

    ImageKit uses tr= parameter with comma-separated transforms:
    e.g., ?tr=w-200,h-200,q-80

    For backwards compatibility, we also support standard query params
    which work with most image CDNs.
    """
    # Build ImageKit-style transformation string
    ik_parts = []
    query_parts = []

    for key, value in params.items():
        if value is not None:
            # Map to ImageKit transform syntax
            if key == "w":
                ik_parts.append(f"w-{value}")
            elif key == "h":
                ik_parts.append(f"h-{value}")
            elif key == "q":
                ik_parts.append(f"q-{value}")
            elif key == "fit":
                # Map fit values to ImageKit crop modes
                fit_map = {
                    "cover": "c-maintain_ratio",
                    "contain": "c-at_max",
                    "fill": "c-force",
                }
                ik_parts.append(fit_map.get(value, f"c-{value}"))
            else:
                query_parts.append(f"{key}={value}")

    if not ik_parts and not query_parts:
        return base_url

    # Use ImageKit tr= parameter if we have ImageKit transforms
    separator = "&" if "?" in base_url else "?"

    if ik_parts:
        tr_param = f"tr={','.join(ik_parts)}"
        if query_parts:
            return f"{base_url}{separator}{tr_param}&{'&'.join(query_parts)}"
        return f"{base_url}{separator}{tr_param}"

    # Fall back to standard query params
    return f"{base_url}{separator}{'&'.join(query_parts)}"
