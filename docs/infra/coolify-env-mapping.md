# Coolify Environment Mapping

This file defines the runtime keys that application containers must resolve from Bitwarden at startup.

## Important

After first Coolify application creation, these keys must be **manually added** to the Coolify application via the UI. Ansible does not push them automatically — only `BWS_ACCESS_TOKEN` and `DOCKER_TAG` are pushed by Ansible.

See [Operator Guide — First deployment](operator-guide.md#first-deployment) for the manual setup procedure.

## Coolify-provided variable

- `BWS_ACCESS_TOKEN` (pushed by Ansible)

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
- `POSTGRES_DB`
- `POSTGRES_HOST`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `REDIS_URL`
- `CELERY_FLOWER_USER`
- `CELERY_FLOWER_PASSWORD`
- `WEB_CONCURRENCY`

## Notes

- Values come from Bitwarden Secrets Manager and are selected by `.key`.
- Keep key names identical across Bitwarden and application settings where possible.
- Coolify does not need to store every runtime variable individually if containers resolve them directly from Bitwarden.
- If a new runtime variable is introduced in application settings, add it here and update deploy preflight validation and runtime bootstrap logic.