from django.utils.translation import gettext_lazy as _
from djstripe.models import WebhookEndpoint as StripeWebhookEndpoint
from wagtail.admin.viewsets.model import ModelViewSet

from neuromancers_network.core.views.stripe import ReadOnlyIndexView


class StripeWebhookEndpointViewSet(ModelViewSet):
    """A read-only listing of synced Stripe webhook endpoints."""

    model = StripeWebhookEndpoint
    index_view_class = ReadOnlyIndexView
    inspect_view_enabled = True
    add_to_reference_index = False
    icon = "cogs"
    menu_label = _("Webhook endpoints")
    menu_name = "stripe_webhook_endpoints"
    menu_order = 9
    list_display = ["url", "status"]
    search_fields = ["url"]
    form_fields = ["url"]
