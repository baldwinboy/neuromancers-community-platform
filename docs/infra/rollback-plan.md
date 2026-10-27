# Rollback Plan

## Scope

This document covers rollback procedures for the NEUROMANCERS Network
application stack deployed via Coolify on the Hetzner VPS.

---

## Rollback scenarios

| Severity | Scenario | Action |
|----------|----------|--------|
| **Low** | Buggy release, no data loss | Redeploy previous Docker image via Coolify UI |
| **Medium** | Broken migration, minor data corruption | Roll back image + restore DB from backup |
| **High** | App completely down, emergency | Stop services, restore full stack from last known-good |

---

## Low severity — Image rollback

Use when the application code is broken but the database schema is
compatible with the previous release.

### Via GitHub Actions (recommended)

1. Go to the **Actions** tab in GitHub.
2. Open **Deploy Infrastructure** and choose **Run workflow**.
3. Run from `main` or `staging` and provide:
   - the previous working commit SHA
   - the matching branch
   - the matching environment
   - `require_health_revision=false` only if the target predates the
     `/api/health` revision field
4. The workflow verifies the image manifests, updates `DOCKER_TAG` to the
   previous SHA, and deploys.
5. Confirm the Ansible assertions: running app containers use `:{sha}` and
   `/api/health.revision` matches.

This is an **image-only rollback**. The Compose file still comes from the
current branch head; it does not roll back Compose or infrastructure changes.

### Via Coolify UI

1. Log into the Coolify dashboard over Tailscale.
2. Navigate to the `neuromancers_network` application.
3. Go to the **Environment variables** tab.
4. Set `DOCKER_TAG` to the previous working commit SHA.
5. Save the variable.
6. Go to the **Deployments** tab and click **Redeploy**.

Do not use `git_commit_sha` as the rollback selector. It does not choose the
image; Coolify uses `git_branch` for the Compose checkout and `DOCKER_TAG` for
the image. Ansible converges `git_commit_sha` to the validated target SHA so
the post-deploy assertion is meaningful.

### Async bootstrap after rollback

After rollback, confirm `django-init` completed. Deployment success does not
prove migrations/seeds completed, and a failed init does not fail the
deployment. On a restored or empty database, run the bootstrap synchronously
before enabling traffic (see
[Operator Guide — Fresh database exception](operator-guide.md#fresh-database-exception)).

Images built before the async bootstrap change have no `/start-init`. On such a
rollback the `django-init` container fails to exec (`/start-init: not found`)
and exits non-zero. This is non-fatal: the service is `exclude_from_hc: true`,
`restart: "no"`, and nothing depends on it. The image's legacy `/start`
performs the bootstrap synchronously; confirm `/api/ready` before enabling
traffic.

### Identify the previous image tag

```bash
# List available image tags from ghcr.io
PACKAGE="neuromancers-network"
curl -s "https://ghcr.io/v2/baldwinboy/${PACKAGE}/tags/list" \
  | jq -r '.tags[]' | sort -V
```

Every build is pushed as a plain `{SHA}` tag. Use that SHA for rollback. The
`:latest` and `:staging` tags are retained for compatibility but are not the
deployment source of truth.

Automated rollback requires that the target image was built by the current
pipeline (content tags and health revision). For older commits, use the
Coolify UI procedure or restore from a database backup as appropriate.

---

## Medium severity — Rollback with database restore

Use when a schema migration must be reverted or data has been corrupted.

### Step 1 — Stop the application

1. In Coolify, stop the `neuromancers_network` application to prevent
   further writes.
2. Wait for all containers to reach stopped state.

### Step 2 — Identify the backup to restore

Backups are stored in S3-compatible storage at the bucket root. The naming
convention is:

```
postgres-YYYYMMDD-HHMMSS.sql.gz
```

Retention is configured via the `RETENTION_DAYS` env var (default: 30).

```bash
# List available backups on the host
ssh deploy@hetzner-tailscale-ip 'ls -lht /opt/backups/'
```

Backups are also uploaded to the bucket root (`s3://$AWS_S3_BUCKET_NAME/`).

### Step 3 — Restore the database

Restore manually on the host:

```bash
# SSH into the host (via Tailscale)
ssh deploy@hetzner-tailscale-ip

# Find the backup
RESTORE_FILE="/opt/backups/postgres-20260628-020000.sql.gz"

# Restore into the running postgres container
gunzip -c "${RESTORE_FILE}" \
  | docker exec -i <postgres-container> \
    psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
```

### Step 4 — Redeploy the previous image

Follow the **Low severity** procedure above to redeploy with the
previous working image tag.

### Step 5 — Verify

1. Confirm the app starts without errors.
2. Run smoke checks (health endpoint returns 200).
3. Verify key user-facing functionality.

---

## High severity — Emergency containment

Use when the application is completely unavailable or under active
incident (security breach, data leak, total outage).

### Immediate containment

1. **Disable Coolify auto-deploy:**
   - In Coolify, navigate to the application settings.
   - Disable **Auto Deploy**.
   - This prevents a webhook deployment racing the CI/CD path.

2. **Stop application containers:**
   - In Coolify, stop the `neuromancers_network` application.
   - If Coolify is unreachable, SSH into the host and stop containers:
     ```bash
     docker compose -f /data/coolify/proxy/docker-compose.yml down
     docker stop $(docker ps -q)
     ```

3. **Assess the scope:**
   - Check application and postgres logs.
   - Determine if data was affected.
   - Determine if it is a code issue, config issue, or infrastructure issue.

### Recovery

- **Code issue:** Follow medium-severity rollback procedure.
- **Config issue:** Fix the env var or config, redeploy.
- **Infrastructure issue:** Run the Ansible playbook to reconfigure the host:
  ```bash
  bws run -- ansible-playbook infra/playbooks/site.yml \
    --inventory infra/inventory/hosts.yml \
    --private-key infra/inventory/ssh_key \
    --extra-vars "git_branch=staging git_commit_sha=<40-char-sha> git_environment=staging postgres_tag=postgres-<tree-sha> require_health_revision=true verify_source_sha=false"
  ```
  Use the same extra-vars as the CI deploy. There is no `setup_coolify`
  tag — `--tags setup_coolify` would silently run nothing.
- **Data breach:** Rotate all secrets in Bitwarden, generate new
  `BWS_ACCESS_TOKEN`, update GitHub environment secrets, redeploy.

### Post-incident

1. File an incident report.
2. Determine root cause.
3. Add preventive measures (automated tests, additional monitoring,
   hardened configuration).
4. Update this rollback plan if gaps were found.

---

## Rollback decision tree

```
Is the app completely down?
├── Yes → Emergency containment
└── No → Is data corrupted?
    ├── Yes → Medium severity (DB restore + image rollback)
    └── No → Low severity (image rollback only)
```

---

## Preventing rollbacks

- Run full CI pipeline (lint + test + migration check) before merging.
- Use the staging environment to validate changes before production.
- Ensure `manage.py migrate` runs in the dedicated production bootstrap
  (`django-init` / `manage.py bootstrap`) before traffic is enabled, so schema
  changes are always applied in the correct order.
- Test DB migrations against a copy of production data in staging.
- Keep rollback-tolerant code patterns (backward-compatible
  migrations, feature flags for risky changes).
