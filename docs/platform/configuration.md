# Configuration

## Environment variables

The authoritative list is `.env.example` and
[`../infra/coolify-env-mapping.md`](../infra/coolify-env-mapping.md). The
important ones:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret **and the key-encryption key (KEK)** for encrypted integration secrets. |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` in deployed environments. |
| `DATABASE_URL` | PostgreSQL connection URL. |
| `REDIS_URL` / cache URLs | Cache and Celery broker/result backend. |
| `DJANGO_AWS_*`, `AWS_*` | Media storage and private exports storage. |
| `STRIPE_*` (optional bootstrap) | Legacy environment bootstrap; runtime Stripe keys are database settings. |

Model/service API keys (Stripe, Whereby, Daily, GetPronto, SMTP) are **not**
environment variables in normal operation — they are Wagtail settings edited in
the admin and encrypted at rest. See the
[secrets runbook](../infra/secrets-runbook.md) for storage and rotation.

## Encrypted settings

`core/models/settings.py` uses `EncryptedCharField` (`core/fields.py`) for:

- `StripeSettings.secret_key`, `webhook_secret`, `client_id`
- `EmailSettings.password`
- `IntegrationSettings.getpronto_api_key`, `whereby_api_key`, `daily_api_key`,
  `whereby_webhook_secret`, `daily_webhook_secret`

Fernet keys are derived as `urlsafe_b64encode(sha256(DJANGO_SECRET_KEY))`
(`core/crypto.py`). Empty `DJANGO_SECRET_KEY` fails fast. Secret inputs are
masked; leaving one blank keeps the stored value. Rotating the KEK makes existing
ciphertext unreadable — `manage.py check` reports `core.E001` and the runbook
documents recovery ([rotation procedure](../infra/secrets-runbook.md#rotating-django_secret_key-encrypted-database-settings)).
Secret fields are excluded from Wagtail revisions (the settings models are not
revision-enabled).

## Runtime settings models

| Model | Controls |
|---|---|
| `StripeSettings` | Keys, charge type, application fee, tax mode, Connect country/onboarding URLs, subscriptions toggle. |
| `IntegrationSettings` | Meeting provider, room prefix, join-window lead, provider/webhook keys. |
| `LocalizationSettings` | Offered languages, default language, display currency, exchange-rate source and manual rates. |
| `AccountSettings` | Deletion grace and re-registration cooldown. |
| `ModerationSettings` | Blocked username defaults. |
| `NotificationSettings` | Default opt-outs and transactional events. |
| `ScriptsSetting` | Admin-authored head/body scripts. |
| `ConsentSettings` | Banner copy and policy version. |

## Migrations and seed data

Bootstrap is split by environment:

| Context | Entry point | What runs |
|---------|-------------|-----------|
| Local development | `compose/local/django/start` | `migrate`, `ensure_superuser`, seeds, then `runserver_plus`. |
| Production web | `compose/production/django/start` | `collectstatic --noinput`, then Gunicorn. |
| Production init | `compose/production/django/start-init` → `manage.py bootstrap` | `migrate --noinput`, `ensure_superuser`, `seed_help_guide --force`, `seed_pages`, `seed_account_selfservice --force`. |

Production `django-init` is a one-shot asynchronous Compose service. The web
health check does not cover migrations or seeds; check the init service after
deployment. A failed init does not fail the deployment. On a fresh database,
run the init synchronously once before the first deployment (see
[operator guide](../infra/operator-guide.md#fresh-database-exception)).

`seed_help_guide --force` refreshes code-owned Admin Guide rows.
`seed_account_selfservice --force` refreshes the seeded Settings page body and
account feed definitions. `seed_pages` is non-force and only creates missing
pages, menus, and feeds. Admin edits to overwritten content are lost on deploy.

## Feature flags and settings of note

- `IntegrationSettings.meeting_provider` — `whereby` or `daily`.
- `IntegrationSettings.joining_lead_minutes` — join window lead.
- `StripeSettings.subscription_enabled` — server-enforced subscribe gate.
- `StripeSettings.charge_type` — `direct` or `destination` (`separate` retired).
- `PeerProfile.reviews_require_approval` / `accepts_reviews` — per-peer review
  policy.
- `ConsentSettings.policy_version` — bump to re-ask for consent.
