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

## Seeds on container start

`compose/production/django/start` and `compose/local/django/start` run:

```sh
python /app/manage.py migrate --noinput
python /app/manage.py ensure_superuser
python /app/manage.py collectstatic --noinput
python /app/manage.py seed_help_guide --force
python /app/manage.py seed_pages
python /app/manage.py seed_account_selfservice
```

`seed_help_guide --force` refreshes code-owned Admin Guide rows; admin edits to
those rows are overwritten on deploy (see
[operator guide](../infra/operator-guide.md#help-content-on-deploy)). The other
seeders are non-force and never overwrite admin edits.

## Feature flags and settings of note

- `IntegrationSettings.meeting_provider` — `whereby` or `daily`.
- `IntegrationSettings.joining_lead_minutes` — join window lead.
- `StripeSettings.subscription_enabled` — server-enforced subscribe gate.
- `StripeSettings.charge_type` — `direct` or `destination` (`separate` retired).
- `PeerProfile.reviews_require_approval` / `accepts_reviews` — per-peer review
  policy.
- `ConsentSettings.policy_version` — bump to re-ask for consent.
