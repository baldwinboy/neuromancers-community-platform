"""Audience mappings for the seeded Settings page."""

ACTION_AUDIENCES = {
    "account.delete_request": ["can_delete_account"],
    "data.export_request": ["can_request_data_export"],
    "calendar.rotate_token": ["can_rotate_calendar_feed"],
    "calendar.revoke_token": ["can_revoke_calendar_feed"],
    "peer.accept_provider_agreement": ["can_accept_provider_agreement"],
    "peer.subscribe": ["can_start_plan"],
    "peer.subscription_pause": ["can_pause_plan"],
    "peer.subscription_resume": ["can_resume_plan"],
    "peer.subscription_cancel": ["can_cancel_plan"],
    "peer.connect_stripe": ["can_connect_stripe"],
    "peer.open_stripe_dashboard": ["can_open_stripe_dashboard"],
    "peer.stripe_disconnect": ["can_disconnect_stripe"],
}

TAB_AUDIENCES = {
    "provider": ["provider_settings"],
}
