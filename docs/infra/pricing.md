# Pricing and running costs

Two kinds of cost matter: what the **platform charges** (configured in the
admin) and what the **platform costs to run** (owned by operations).

## Platform pricing configuration

- **Care-provider plan prices** — `PeerRequirementsSettings.peer_plan_price_ids`
  (Stripe Price IDs a provider subscribes to).
- **Application fee** — `StripeSettings.application_fee` (percentage of each
  payment the platform keeps).
- **Meeting pricing** — set per meeting by the provider: fixed, sliding scale or
  duration tiers.
- **Tax** — `StripeSettings.tax_mode` (`stripe_tax` or `off`).
- **Display currency and exchange** — `LocalizationSettings.display_currency`,
  `currency_exchange_enabled` and `exchange_rate_source`.

Each of these is editable in the Wagtail admin (see the Admin Guide articles
"Configuring platform pricing and fees" and "Configuring Stripe and payouts").

## Infrastructure running costs

| Component | What it charges for |
|---|---|
| **Hetzner** | The fixed monthly host that runs the containers. |
| **Tigris** | Stored data and requests; **zero egress**, Standard about $0.02/GB with a free 5 GB allowance, Class A/B request rates. |
| **Stripe** | Per-transaction fees plus the platform's application fee. |
| **DNS / CDN, Coolify, Tailscale** | Little or nothing at this scale. |

The cost levers are therefore: stored data, traffic, and payment volume. See
[Storage architecture](storage.md) for what is stored where and its retention.

## Single cost picture

- **Storage** → Tigris (media + private backups/exports).
- **Compute** → Hetzner (via Coolify, reached over Tailscale).
- **Payments** → Stripe (transaction fees + application fee).

All figures are indicative; confirm current provider pricing before quoting.
