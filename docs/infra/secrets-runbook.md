# Secrets Runbook

## Source of truth

- All deployment and runtime secrets are stored in Bitwarden Secrets Manager.
- GitHub stores only `BWS_ACCESS_TOKEN`.
- Workflows fetch secret data from Bitwarden during execution.
- Ansible pushes only `BWS_ACCESS_TOKEN`, `DOCKER_TAG`, `TS_APP_DOMAIN`, `TS_PAAS_DOMAIN`, `TAILSCALE_TAG`, `TS_OAUTH_CLIENT_ID`, and `TS_OAUTH_CLIENT_SECRET` to Coolify.
- All other secrets must be manually added to the Coolify application by a developer.
- Application containers receive secrets from Coolify environment variables at startup.

## Initial Coolify secret setup

After Ansible creates the Coolify application for the first time, a developer must manually add secrets:

1. Log into the Coolify dashboard over Tailscale.
2. Navigate to the `neuromancers_network` application.
3. Go to the **Environment variables** tab.
4. For each secret you want the application to use, add a new variable:
   - **Key**: the Bitwarden key name (e.g. `DJANGO_SECRET_KEY`)
   - **Value**: the actual value from Bitwarden (can be a stub initially)
   - **Is Literal**: true (values are not template variables)
5. Save the changes. Coolify will restart the affected containers.

The Ansible playbook refreshes only Bitwarden secrets whose keys already exist in Coolify. The seven keys listed above are always pushed; any other new key must be added in Coolify first.

When member data exports are enabled, the root `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET_NAME`, `AWS_REGION` and `AWS_ENDPOINT_URL_S3` keys must be added here too (in addition to the `DJANGO_AWS_*` media keys), because the container reads them for the private `exports` storage alias. `RETENTION_DAYS` and `AWS_ENDPOINT_URL_IAM` are server-only and do not belong in the Coolify application environment.

## Bitwarden CLI constraints

- `bws secret list` returns a JSON array of objects.
- Each object has `key` and `value` fields.
- There is no direct `get by key` command.
- To obtain one or more named secrets, list and filter with `jq`.
- To run an entire command with secrets injected, use `bws run -- '<command>'`.

Example filter:

```bash
bws secret list | jq -r '.[] | select(.key=="DJANGO_SECRET_KEY") | .value'
```

Example command injection:

```bash
bws run -- 'ansible-playbook infra/playbooks/site.yml --inventory infra/inventory/hosts.yml'
```

## Storage matrix

### GitHub

- `BWS_ACCESS_TOKEN`

### Coolify

- `BWS_ACCESS_TOKEN`
- `TAILSCALE_TAG` (also pushed by Ansible)

### Bitwarden Secrets Manager

- `CELERY_FLOWER_PASSWORD`
- `CELERY_FLOWER_USER`
- `COOLIFY_ADMIN_EMAIL`
- `COOLIFY_ADMIN_PASSWORD`
- `COOLIFY_ADMIN_USERNAME`
- `GATUS_DISCORD_WEBHOOK_URL`
- `DJANGO_ACCOUNT_ALLOW_REGISTRATION`
- `DJANGO_ADMIN_URL`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_AWS_ACCESS_KEY_ID`
- `DJANGO_AWS_SECRET_ACCESS_KEY`
- `DJANGO_AWS_STORAGE_BUCKET_NAME`
- `DJANGO_AWS_S3_REGION_NAME`
- `DJANGO_AWS_S3_ENDPOINT_URL`
- `DJANGO_AWS_S3_ADDRESSING_STYLE`
- `DJANGO_AWS_S3_CUSTOM_DOMAIN`
- `DJANGO_SECRET_KEY`
- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SERVER_EMAIL`
- `DJANGO_SETTINGS_MODULE`
- `HETZNER_SSH_HOST`
- `HETZNER_SSH_PRIVATE_KEY`
- `HETZNER_SSH_USER`
- `POSTGRES_DB`
- `POSTGRES_HOST`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `REDIS_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_S3_BUCKET_NAME`
- `AWS_REGION`
- `AWS_ENDPOINT_URL_S3`
- `AWS_ENDPOINT_URL_IAM`
- `RETENTION_DAYS`
- `TAILSCALE_TAG`
- `TS_OAUTH_CLIENT_ID`
- `TS_OAUTH_CLIENT_SECRET`
- `WEB_CONCURRENCY`
- `HETZNER_SSH_PUBLIC_KEY`

The root `AWS_*` keys back the private `exports` storage alias for member data exports, distinct from the `DJANGO_AWS_*` public-media credentials. The application container needs `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET_NAME`, `AWS_REGION` and `AWS_ENDPOINT_URL_S3`. `RETENTION_DAYS` and `AWS_ENDPOINT_URL_IAM` are used only by the server-side backup cron (`infra/scripts/backup.sh`), not the container. See [Storage architecture](storage.md).

`DJANGO_AWS_S3_ENDPOINT_URL` is the S3 API host (for Tigris, `t3.storage.dev`). `DJANGO_AWS_S3_CUSTOM_DOMAIN` is the bucket's public hostname (for example `neuromancers-network-staging.t3.tigrisfiles.io`). It must be a bare hostname, not the endpoint and not a URL.

## Rotation procedure

1. Rotate secret in source provider.
2. Update Bitwarden entry value for the same key.
3. Run a staging deploy and verify health checks.
4. Run a production deploy and verify health checks.
5. Revoke old credential.

### Rotating `DJANGO_SECRET_KEY` (encrypted database settings)

`DJANGO_SECRET_KEY` is also the key-encryption key for integration secrets
stored in Wagtail settings (Stripe keys, SMTP password, GetPronto/Whereby/Daily
API keys). Those fields are Fernet-encrypted at rest and cannot be recovered
with a different key.

1. Apply the normal rotation steps above to update `DJANGO_SECRET_KEY`.
2. Deploy; `manage.py check` (and the deploy health check) fails with
   `core.E001` if any stored secret cannot be decrypted.
3. Re-enter each integration secret in the Wagtail admin (leave the field blank
   to keep a working value; enter the value again after a rotation).
4. Re-run `manage.py check` until `core.E001` is clear.
5. Rotating back to the old key restores access to the old ciphertext, but the
   re-entered values are encrypted with the new key — re-enter once more if you
   roll the key back for good.

## Minimum CI preflight checks

1. Validate `BWS_ACCESS_TOKEN` is present in the active GitHub environment.
2. Validate required Bitwarden keys exist before starting deploy mutation.
	Deploy minimum includes `HETZNER_SSH_HOST`, `HETZNER_SSH_PRIVATE_KEY`, `HETZNER_SSH_USER`, `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_CLIENT_SECRET`, `TAILSCALE_TAG`, `COOLIFY_ADMIN_USERNAME`, `COOLIFY_ADMIN_EMAIL`, `COOLIFY_ADMIN_PASSWORD`, `COOLIFY_ADMIN_TOKEN`, plus the runtime keys in [Coolify Env Mapping](../infra/coolify-env-mapping.md).
3. Fail fast if any required key is missing or empty.
4. Mask every extracted secret before writing to step outputs or logs, including every line of multi-line values.

## Runtime prerequisites

1. Every production image that needs runtime secrets must include the BWS CLI.
2. Every production entrypoint must resolve its required Bitwarden keys before starting the app process.
3. Runtime startup must fail fast if a required Bitwarden key is missing.
4. Runtime secret bootstrap must not print secret values to logs.