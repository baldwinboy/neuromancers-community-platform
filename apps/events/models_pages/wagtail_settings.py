from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting


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
    account_id = models.CharField(
        "Account ID",
        help_text=(
            "Your organisation's Stripe Connect account ID. "
            "This can be gotten from your Stripe dashboard settings. Starts with 'acct_'"
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
