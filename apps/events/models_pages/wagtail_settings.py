from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, FieldRowPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.fields import StreamField, StreamValue

from apps.events.validators import slug_validator


@register_setting(icon="stripe")
class StripeSettings(BaseGenericSetting):
    publishable_key = models.CharField(
        "API Publishable Key",
        help_text=(
            "Your organisation's Stripe API Publishable Key. "
            "This can be gotten from your Stripe dashboard. Starts with 'pk_'"
        ),
        max_length=255,
        null=True,
        blank=True,
    )
    secret_key = models.CharField(
        "API Secret Key",
        help_text=(
            "Your organisation's Stripe API Secret Key. "
            "This can be gotten from your Stripe dashboard. Starts with 'sk_'"
        ),
        max_length=255,
        null=True,
        blank=True,
    )
    client_id = models.CharField(
        "Client ID",
        help_text=(
            "Your organisation's Stripe Connect client ID. "
            "This can be gotten from your Stripe dashboard settings. Starts with 'ca_'"
        ),
        max_length=255,
        null=True,
        blank=True,
    )
    redirect_url = models.URLField(
        "Redirect URL",
        help_text=(
            "The URL that you'd like users to be directed to after payments"
            " are made using Stripe's embedded elements"
        ),
        null=True,
        blank=True,
    )
    application_fee = models.PositiveSmallIntegerField(
        "Application fee (%)",
        help_text="The percentage of each payment that you'd like to take from users.",
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Stripe API Settings"


@register_setting(icon="whereby")
class WherebySettings(BaseGenericSetting):
    api_key = models.TextField(
        "API Key",
        help_text=(
            "Your organisation's Whereby API key. "
            "This can be gotten from your Whereby dashboard."
        ),
        max_length=1024,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Whereby API Settings"


class FilterItemBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, help_text="Display label")
    slug = blocks.CharBlock(
        required=False,
        validators=[slug_validator],
        help_text="Stable ID for this item (auto-generated if empty)",
    )

    panels = [FieldRowPanel(("label", "slug"))]

    def clean(self, value):
        value = super().clean(value)
        if not value.get("slug") and value.get("label"):
            # Auto-generate slug from label
            value["slug"] = slugify(value["label"])
        return value

    class Meta:
        icon = "tag"
        collapsed = True
        label_format = "{label} ({slug})"
        form_classname = "filter-item-block struct-block flex flex-wrap gap-8"


class FilterGroupBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, help_text="Filter group label")
    slug = blocks.CharBlock(
        required=False,
        validators=[slug_validator],
        help_text="Stable ID for this filter group (auto-generated if empty)",
    )
    items = blocks.ListBlock(FilterItemBlock(), help_text="Filter items")

    panels = [FieldRowPanel(("label", "slug")), FieldPanel("items")]

    def clean(self, value):
        value = super().clean(value)
        if not value.get("slug") and value.get("label"):
            value["slug"] = slugify(value["label"])
        return value

    class Meta:
        icon = "list-ul"
        collapsed = True
        label_format = "{label} ({slug})"
        form_classname = "filter-group-block struct-block flex flex-wrap gap-8"


CACHE_KEY = "filter_settings_normalized"
CACHE_TIMEOUT = 60 * 60  # 1 hour (or None for no expiry)


@register_setting(icon="filter")
class FilterSettings(BaseGenericSetting):
    filters = StreamField(
        [
            ("group", FilterGroupBlock()),
        ],
        use_json_field=True,
    )  # use JSONField for simplicity

    panels = [
        FieldPanel("filters"),
    ]

    class Meta:
        verbose_name = "Session filters"

    def as_normalized_mapping(self):
        """
        Convert StreamValue into:
        {
          "<group_slug>": {
            "label": "...",
            "slug": "...",
            "items": {
               "<item_slug>": { ... }
            }
          }
        }
        """
        normalized = {}

        if not isinstance(self.filters, StreamValue):
            return normalized

        for group in self.filters.get_prep_value():
            g = group.get("value")
            g_slug = g.get("slug")
            g_label = g.get("label")
            items = g.get("items", [])

            if not g_slug:
                continue

            normalized[g_slug] = {"slug": g_slug, "label": g_label, "items": {}}

            for item in items:
                iv = item.get("value")
                i_slug = iv.get("slug")
                i_label = iv.get("label")

                if not i_slug:
                    continue

                normalized[g_slug]["items"][i_slug] = {
                    "slug": i_slug,
                    "label": i_label,
                }

        return normalized

    @classmethod
    def get_cached_mapping(cls):
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return cached

        instance = cls.load()
        mapping = instance.as_normalized_mapping()

        cache.set(CACHE_KEY, mapping, CACHE_TIMEOUT)
        return mapping

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate cache on save
        cache.delete(CACHE_KEY)


@register_setting(icon="image")
class ImageUploadSettings(BaseGenericSetting):
    get_pronto_api_key = models.CharField(
        "Get Pronto API Key",
        help_text=(
            "Your Get Pronto API key. This can be obtained from your Get Pronto dashboard."
        ),
        max_length=255,
        null=True,
        blank=True,
    )
    get_pronto_api_url = models.URLField(
        "Get Pronto API URL",
        help_text=(
            "The base URL for the Get Pronto API. This is typically in the format 'https://api.getpronto.com/v1/'"
        ),
        null=True,
        blank=True,
        default="https://api.getpronto.io/v1/",
    )
    get_pronto_email = models.EmailField(
        "Get Pronto Email",
        help_text=("The email address associated with your Get Pronto account."),
        null=True,
        blank=True,
    )
    get_pronto_password = models.CharField(
        "Get Pronto Password",
        help_text=("The password for your Get Pronto account."),
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Image Upload API Settings"
