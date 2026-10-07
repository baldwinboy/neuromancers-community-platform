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
- `DJANGO_AWS_S3_ENDPOINT_URL`
- `DJANGO_AWS_S3_ADDRESSING_STYLE`
- `DJANGO_AWS_S3_CUSTOM_DOMAIN`
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
- `TS_METRICS_DOMAIN`

## Notes

- Values come from Bitwarden Secrets Manager and are selected by `.key`.
- Keep key names identical across Bitwarden and application settings where possible.
- Coolify does not need to store every runtime variable individually if containers resolve them directly from Bitwarden.
- `TS_METRICS_DOMAIN` is consumed by `config/settings/production.py` and must be present in Coolify even though it is not pushed by Ansible.
- If a new runtime variable is introduced in application settings, add it here and update deploy preflight validation and runtime bootstrap logic.