# Storage architecture (Tigris)

All files are stored in **Tigris**, an S3-compatible object store. There are two
buckets with different exposure and lifecycles.

## Public media bucket

- Holds things that are safe to serve directly: avatars, uploaded images and
  admin documents. **No personal data exports and no backups belong here.**
- Configured with the `DJANGO_AWS_*` variables and served through the custom
  domain (`DJANGO_AWS_S3_CUSTOM_DOMAIN`, e.g. `t3.storage.dev`).
- Backed by the `default` storage alias (`STORAGES["default"]`, location
  `media`).

## Private backups bucket

- Holds database/media **backups** and member **data exports**. It is never
  served publicly.
- Configured with the **root** `AWS_*` variables (the backup credentials), not
  the `DJANGO_AWS_*` media ones.
- Backups are pruned by the maintenance script after `RETENTION_DAYS`
  (default 30).

## Private exports (`exports/`)

Member data exports are written by the data-export pipeline to the private
backups bucket under an `exports/` prefix, via the dedicated `exports` storage
alias:

- `STORAGES["exports"]` points at the private bucket, location `exports`,
  `querystring_auth=True` (short-lived signed URLs).
- In development and tests the alias is a local `FileSystemStorage` under
  `neuromancers_network/exports/`.
- Exports are downloaded through a signed, owner/staff-only view
  (`/exports/<pk>/<token>/`), never a public URL.
- Exports expire after **48 hours**; `sweep_data_exports` retries stale jobs and
  purges expired ones hourly. There is no lifecycle-rule automation in scope.

## Retention summary

| Data | Location | Retention |
|---|---|---|
| Avatars, images, documents | public media bucket | until removed |
| Backups | private backups bucket | `RETENTION_DAYS` (default 30) |
| Data exports | private backups bucket, `exports/` | 48 hours |

## Environment mapping

| Setting | Purpose | Key |
|---|---|---|
| `STORAGES["default"]` | public media bucket | `DJANGO_AWS_*` |
| `STORAGES["exports"]` | private exports | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET_NAME`, `AWS_REGION`, `AWS_ENDPOINT_URL_S3` |

See [Coolify environment mapping](coolify-env-mapping.md) and the
[Secrets runbook](secrets-runbook.md).
