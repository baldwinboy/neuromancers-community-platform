import logging
from django import template
from django.conf import settings
from django.core.cache import cache

from neuromancers_network.common.mjml import MJMLClient
from neuromancers_network.core.models import ExternalAPISettings

register = template.Library()
logger = logging.getLogger(__name__)


def get_mjml_client():
    try:
        api_settings = ExternalAPISettings.load()
        return MJMLClient(
            application_id=api_settings.mjml_app_id,
            secret_key=api_settings.mjml_secret_key,
            base_url=getattr(settings, "MJML_API_BASE_URL",
                             "https://api.mjml.io/v1"),
            timeout=getattr(settings, "MJML_API_TIMEOUT", 30),
        )
    except ExternalAPISettings.DoesNotExist:
        logger.warning(
            "MJML API settings not found. MJML rendering will not work.")
        return MJMLClient(
            application_id=None,
            secret_key=None,
            base_url=getattr(settings, "MJML_API_BASE_URL",
                             "https://api.mjml.io/v1"),
            timeout=getattr(settings, "MJML_API_TIMEOUT", 30),
        )


@register.tag(name="mjml")
def mjml_tag(parser, token):
    """
    Template tag that renders MJML content to HTML.

    Usage:
        {% load mjml_tags %}
        {% mjml %}
            <mjml>
                <mj-body>
                    <mj-section>
                        <mj-column>
                            <mj-text>Hello, {{ user.name }}!</mj-text>
                        </mj-column>
                    </mj-section>
                </mj-body>
            </mjml>
        {% endmjml %}

    The tag also supports caching via the 'cache' parameter:
        {% mjml cache="email_template:homepage" %}
            ...
        {% endmjml %}

    And an optional timeout (in seconds):
        {% mjml cache="my_template" cache_timeout=3600 %}
            ...
        {% endmjml %}
    """
    return MJMLNode(parser, token)


class MJMLNode(template.Node):

    def __init__(self, parser, token):
        self.parser = parser
        self.cache_key = None
        self.cache_timeout = None

        # Parse arguments like cache="key" and cache_timeout=seconds
        bits = token.split_contents()
        for bit in bits[1:]:
            if "=" not in bit:
                raise template.TemplateSyntaxError(
                    f"Invalid argument: {bit}. Use cache='key' and/or cache_timeout=seconds"
                )
            key, value = bit.split("=", 1)
            if key == "cache":
                self.cache_key = template.Variable(value)
            elif key == "cache_timeout":
                self.cache_timeout = template.Variable(value)
            else:
                raise template.TemplateSyntaxError(f"Unknown argument: {key}")

    def render(self, context):
        # Resolve the cache key and timeout if provided
        cache_key = None
        if self.cache_key:
            cache_key = self.cache_key.resolve(context)
            if not cache_key:
                cache_key = None

        cache_timeout = None
        if self.cache_timeout:
            try:
                cache_timeout = int(self.cache_timeout.resolve(context))
            except (ValueError, TypeError):
                pass

        # 1. Try to get from cache
        if cache_key:
            cached_html = cache.get(cache_key)
            if cached_html is not None:
                return cached_html

        # 2. Parse the MJML content from the template block
        nodelist = self.parser.parse(("endmjml", ))
        self.parser.delete_first_token()
        mjml_content = nodelist.render(context)

        # 3. Render via MJML API
        try:
            client = get_mjml_client()
            html_output = client.render_to_html(mjml_content)

            # 4. Store in cache if requested
            if cache_key:
                cache.set(cache_key, html_output, cache_timeout)

            return html_output

        except Exception as e:
            logger.error(f"MJML rendering failed: {e}", exc_info=True)
            # Fallback to the raw MJML content wrapped in a comment
            return (f"<!-- MJML rendering error: {str(e)} -->\n"
                    f"<!-- Raw MJML content:\n{mjml_content}\n-->")
