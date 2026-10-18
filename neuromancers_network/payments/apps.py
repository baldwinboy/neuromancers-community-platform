import stripe
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

STRIPE_TIMEOUT_SECONDS = 20


class PaymentsConfig(AppConfig):
    name = "neuromancers_network.payments"
    verbose_name = _("Payments")

    def ready(self):
        """
        Override this method in subclasses to run code when Django starts.
        """
        from . import signals  # noqa: F401, PLC0415

        if stripe.default_http_client is None:
            stripe.default_http_client = stripe.RequestsClient(
                timeout=STRIPE_TIMEOUT_SECONDS,
            )
