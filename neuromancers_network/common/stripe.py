import stripe
from django.apps import apps


def _extract_link_block_url(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        link_to = value.get("link_to")
        if link_to and link_to in value:
            val = value[link_to]
            return val if isinstance(val, str) else ""
        return value.get("custom_url") or value.get("url") or ""
    return str(value)


class Stripe:

    def __init__(self):
        ExternalAPISettings = apps.get_model("core", "ExternalAPISettings")
        external_api_settings = ExternalAPISettings.load()
        self.secret_key = external_api_settings.stripe_secret_key
        self.publishable_key = external_api_settings.stripe_publishable_key
        self.application_fee = external_api_settings.stripe_application_fee
        self.client_id = external_api_settings.stripe_client_id
        self.redirect_url = _extract_link_block_url(
            external_api_settings.stripe_onboarding_redirect_url,
        )
        self.refresh_url = _extract_link_block_url(
            external_api_settings.stripe_onboarding_refresh_url,
        )
        self.client = stripe.StripeClient(
            api_key=self.secret_key,
            client_id=self.client_id,
        )

    def get_oauth_token(self, code: str):
        return self.client.OAuth.token(grant_type="authorization_code",
                                       code=code)

    def get_oauth_url(self):
        return self.client.OAuth.authorize_url(
            response_type="code",
            scope="read_write",
            redirect_uri=self.redirect_url,
        )

    def is_account_ready(self, stripe_account_id: str) -> bool:
        account = self.client.Account.retrieve(stripe_account_id)
        return (account.charges_enabled and account.payouts_enabled
                and account.details_submitted)
