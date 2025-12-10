DEFAULT_NOTIFICATION_SETTINGS = {
    "requested_session": 1,
    "responded_session": 1,
    "cancelled_session": 1,
    "session_reminders": 1,
    "account_deleted": 1,
    "payment_made": 1,
    "payment_refunded": 1,
}

DEFAULT_PEER_NOTIFICATION_SETTINGS = {
    **DEFAULT_NOTIFICATION_SETTINGS,
    **{
        "published_session": 1,
        "host_session_requested": 1,
        "host_session_booked": 1,
        "host_session_cancelled": 1,
        "host_session_reminders": 1,
        "payment_received": 1,
        "payment_refund_request": 1,
        "payment_refunded": 1,
    },
}
