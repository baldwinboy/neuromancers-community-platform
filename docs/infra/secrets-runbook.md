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

## Rotation procedure

1. Rotate secret in source provider.
2. Update Bitwarden entry value for the same key.
3. Run a staging deploy and verify health checks.
4. Run a production deploy and verify health checks.
5. Revoke old credential.

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