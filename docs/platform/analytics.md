# Analytics

The `analytics` app is ledger-first: every metric is derived from append-only
ledgers, not from mutable counters.

## Ledgers

| Model | Contents |
|---|---|
| `TransactionLedger` | Marketplace money — `booking_payment`, `refund`, `application_fee`, `dispute`. Base + presentment currency/amounts, persisted `exchange_rate`, `fee_amount`, `net_amount`, payer/payee, provider object id, `occurred_at`. |
| `SubscriptionLedger` | Recurring platform revenue — `subscription_payment`/`subscription_refund`, invoice/subscription ids. Kept separate from marketplace money. |
| `SessionLedger` | Delivered minutes per session (OneToOne `MeetingRequest`) or per group `Meeting`, with `provider`. |
| `ActivityLedger` | Temporal facts (payments, refunds, disputes, webhook deliveries) for funnel/activity metrics. |

Every row carries a unique `idempotency_key`; writers use
`update_or_create`, so webhook replays and backfills converge on one row.

## Writers

- `meetings/signals.py`:
  - `checkout.session.completed` — one payment per line item, one application
    fee (PaymentIntent `application_fee_amount`, else the configured percent),
    activity rows.
  - `charge.refunded` — the actual `refund_data["amount"]` for every refund,
    negative, plus activity.
  - `charge.dispute.*` — dispute rows.
- `peers/signals.py` — `invoice.payment_succeeded`/`invoice.paid` →
  `SubscriptionLedger` (subscription revenue).
- `meetings/tasks.py` — completed sessions write `SessionLedger` rows.
- `core/views/provider_webhooks.py` — Whereby/Daily webhooks upsert session
  minutes (and attendance on the session models).

Provider timestamps (`created`, `start_ts`/`end_ts`) are used for
`occurred_at`, so replays are deterministic. Rates are stored as **base per
presentment**; currency conversion prefers the persisted checkout rate.

## Metrics

`analytics/metrics.py` is a pure, `now`-injectable layer:

- Periods: `this_month`, `last_month`, `last_3_months`, `all_time` (UTC months).
- Scopes: platform, peer (`payee`), member (`payer`).
- Metrics: GBV, application fees, take rate, refunds + rate, disputes, AOV,
  active members/peers (ledger actors), repeat-booking rate, published-review
  rate, session minutes by provider, subscription revenue, requests/bookings by
  status, and per-currency + converted totals.

`convert_amount` (`core/currency.py`) accepts an explicit rate, then
`"SOURCE:TARGET"` manual rates, then the legacy `{target: rate}` form; `stripe`
amounts are already converted at checkout.

## Surfaces

- Staff dashboard at `/cms/analytics/` (`analytics/views.py`,
  `analytics/panels.py`, `analytics/wagtail_hooks.py`) with period selector and
  marketplace/subscription/combined revenue.
- Admin homepage panel with this month’s revenue split.
- `metric_chart` content block (server-computed monthly series, wagtailcharts).
- Read-only API: `/api/analytics/platform` (staff) and `/api/analytics/me`
  (self; peer view for providers).

## Backfill

`analytics.tasks.sync_analytics_ledgers_task` calls `sync_analytics_ledgers()`
to rebuild payment/refund rows from local records idempotently. It is a
maintenance task, not scheduled by default.
