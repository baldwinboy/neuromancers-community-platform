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

### Via Coolify UI

1. Log into Coolify dashboard over Tailscale.
2. Navigate to the `neuromancers_network` application.
3. Go to the **Environment variables** tab.
4. Update `DOCKER_TAG` to the previous working tag or SHA:
   - Production: `previous-sha` (e.g. `abc123def456`)
   - Staging: `staging-previous-sha` (e.g. `staging-abc123def456`)
5. Save the variable.
6. Go to the **Deployments** tab and click **Redeploy**.

### Via GitHub Actions (re-run)

1. Go to the **Actions** tab in GitHub.
2. Find the last successful CI run for the working commit.
3. In the CI workflow run, scroll to the **deploy** job.
4. Re-run the `Deploy Infrastructure` workflow.
5. Confirm the Ansible playbook converges and Coolify redeploys.

### Identify the previous image tag

```bash
# List available image tags from ghcr.io
PACKAGE="neuromancers-network"
curl -s "https://ghcr.io/v2/baldwinboy/${PACKAGE}/tags/list" \
  | jq -r '.tags[]' | sort -V
```

The `:latest` tag represents the last production deploy. The commit SHA
tags (plain SHA for production, `staging-{SHA}` for staging) allow you
to pin to a specific version.

---

## Medium severity — Rollback with database restore

Use when a schema migration must be reverted or data has been corrupted.

### Step 1 — Stop the application

1. In Coolify, stop the `neuromancers_network` application to prevent
   further writes.
2. Wait for all containers to reach stopped state.

### Step 2 — Identify the backup to restore

Backups are stored in S3-compatible storage. The naming convention is:

```
{DB_NAME}_YYYY-MM-DD_HH:MM:SS.sql.gz
```

Retention is configured via the `RETENTION_DAYS` env var (default: 30).

```bash
# List available backups via the awscli container
docker compose -f docker-compose.production.yml run --rm awscli \
  s3 ls s3://${AWS_S3_BUCKET_NAME}/backups/
```

Alternatively, SSH into the Hetzner host and inspect `/opt/backups/`.

### Step 3 — Restore the database

Via the maintenance script on the host:

```bash
# SSH into the host (via Tailscale)
ssh deploy@hetzner-tailscale-ip

# Run the restore script — it will list backups and prompt for selection
sudo /opt/scripts/restore.sh
```

Or manually:

```bash
# Find the backup
RESTORE_FILE="/opt/backups/${DB_NAME}_2026-06-28_02:00:00.sql.gz"

# Restore into the running postgres container
gunzip -c "${RESTORE_FILE}" \
  | docker exec -i neuromancers-postgres-1 \
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
   - Change the deployment branch to a non-existent branch.
   - This prevents automatic redeployment on git push.

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
- **Infrastructure issue:** Run the Ansible playbook with the
  `setup_coolify.yml` tag to reconfigure the host:
  ```bash
  bws run -- ansible-playbook infra/playbooks/site.yml \
    --tags setup_coolify
  ```
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
- Ensure `manage.py migrate` runs at container startup so schema
  changes are always applied in the correct order.
- Test DB migrations against a copy of production data in staging.
- Keep rollback-tolerant code patterns (backward-compatible
  migrations, feature flags for risky changes).
