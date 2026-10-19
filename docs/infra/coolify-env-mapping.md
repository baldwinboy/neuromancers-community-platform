# Coolify Environment Mapping

This file defines the runtime keys that application containers must resolve from Bitwarden at startup.

## Important

After first Coolify application creation, these keys must be **manually added** to the Coolify application via the UI. Ansible only pushes `BWS_ACCESS_TOKEN`, `DOCKER_TAG`, `TS_APP_DOMAIN`, `TS_PAAS_DOMAIN`, `TAILSCALE_TAG`, `TS_OAUTH_CLIENT_ID` and `TS_OAUTH_CLIENT_SECRET`.

See [Operator Guide — First deployment](operator-guide.md#first-deployment) for the manual setup procedure.

## Coolify-provided variables (pushed by Ansible)

- `BWS_ACCESS_TOKEN`
- `DOCKER_TAG`
- `TS_APP_DOMAIN`
- `TS_PAAS_DOMAIN`
- `TAILSCALE_TAG`
- `TS_OAUTH_CLIENT_ID`
- `TS_OAUTH_CLIENT_SECRET`

## Canonical runtime keys (manually added to Coolify)

- `DJANGO_ACCOUNT_ALLOW_REGISTRATION`
- `DJANGO_ADMIN_URL`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_AWS_ACCESS_KEY_ID`
- `DJANGO_AWS_SECRET_ACCESS_KEY`
- `DJANGO_AWS_STORAGE_BUCKET_NAME`
- `DJANGO_AWS_S3_REGION_NAME`
- `DJANGO_AWS_S3_ENDPOINT_URL` — S3 API host (e.g. `t3.storage.dev`)
- `DJANGO_AWS_S3_ADDRESSING_STYLE`
- `DJANGO_AWS_S3_CUSTOM_DOMAIN` — public bucket hostname, bare host (e.g. `<bucket>.t3.tigrisfiles.io`)
- `DJANGO_SECRET_KEY`
- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SERVER_EMAIL`
- `DJANGO_SETTINGS_MODULE`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`
- `DJANGO_SUPERUSER_USERNAME`
- `POSTGRES_DB`
- `POSTGRES_HOST`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `REDIS_URL`
- `CELERY_FLOWER_USER`
- `CELERY_FLOWER_PASSWORD`
- `WEB_CONCURRENCY`
- `GATUS_DISCORD_WEBHOOK_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_S3_BUCKET_NAME`
- `AWS_REGION`
- `AWS_ENDPOINT_URL_S3`

## Server-only keys (not container environment)

These are used by the server-side backup cron (`infra/scripts/backup.sh`), not by
the application container, so they do **not** need to be in the Coolify
application environment:

- `RETENTION_DAYS`
- `AWS_ENDPOINT_URL_IAM`

## Notes

- Values come from Bitwarden Secrets Manager and are selected by `.key`.
- Keep key names identical across Bitwarden and application settings where possible.
- Coolify does not need to store every runtime variable individually if containers resolve them directly from Bitwarden.
- `GATUS_DISCORD_WEBHOOK_URL` is consumed by the `gatus` service in `docker-compose.coolify.yml` and must be present in Coolify even though it is not pushed by Ansible.
- The container `AWS_*` keys (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET_NAME`, `AWS_REGION`, `AWS_ENDPOINT_URL_S3`) back the **private** `exports` storage alias for member data exports — not the public media bucket (which uses `DJANGO_AWS_*`). `AWS_REGION` is required for the exports S3 client.
- If a new runtime variable is introduced in application settings, add it here and update deploy preflight validation and runtime bootstrap logic.