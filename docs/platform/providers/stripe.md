# Stripe

Stripe processes payments, Connect payouts and platform subscriptions. Runtime
configuration lives in `StripeSettings`; secrets are encrypted (see
[Configuration](../configuration.md)).

## Connect and charges

- Providers onboard to **Express** connected accounts via Account Links
  (`payments/services.py::ensure_stripe_account`).
- `charge_type` is `direct` (provider is merchant of record) or `destination`
  (platform charge + transfer). The retired `separate` mode was removed in
  migration `core/0011` and maps to direct.
- Checkout creation is centralised in `payments/charges.py::build_charge_plan`,
  which computes the **application fee** with half-up rounding.
- One line item is created per session; `metadata["line_item_refs"]` maps each
  item back to its `MeetingRequest`/session-less `Booking`. The webhook applies
  Stripe's per-item `amount_total`, never the session total.

## Currency

When the exchange-rate source is Stripe, checkout sends `adaptive_pricing` (only
when enabled). `sync_payment_from_checkout` persists the presentment amount,
presentment currency, base amount and the **base-per-presentment rate** from the
PaymentIntent's `currency_conversion` (falling back to configured rates). The
analytics ledger records the same base/presentment/rate triple.

## Subscriptions

`peer.subscribe` is gated by `StripeSettings.subscription_enabled` and the
provider agreement, then starts a subscription Checkout session. Paid invoices
are recorded in `SubscriptionLedger` from `invoice.payment_succeeded`/
`invoice.paid`. `past_due`/`unpaid` subscriptions trigger the lapse policy
(unpublish ineligible meetings) and pause/resume tracks local state.

## Webhooks

`payments/services.py::DEFAULT_WEBHOOK_EVENTS` lists the platform endpoint
events. Handlers live in `meetings/signals.py` (checkout, payment intent,
refunds, disputes) and `peers/signals.py` (subscriptions and invoices). The
endpoint secret is stored by `create_webhook_endpoint` (refreshing the in-memory
settings object). Webhook processing is idempotent.

## Operations

- Create the endpoint from the Stripe settings panel after the API keys.
- `payments/services.py` sets a global HTTP timeout and uses idempotency keys for
  customer/account creation.
- Secret rotation and payout/disconnect guards are documented in the
  [secrets runbook](../../infra/secrets-runbook.md) and
  [pricing](../../infra/pricing.md).
