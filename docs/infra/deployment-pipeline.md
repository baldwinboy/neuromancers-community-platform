# Deployment Pipeline

## Overview

The deployment pipeline follows a **CI → CD → Coolify** flow. Every
push to `main` or `staging` triggers an automated sequence that builds,
tests, publishes, and deploys the application.

```
Push to main/staging
    │
    ▼
┌────────────────────────────────┐
│  CI (GitHub Actions)           │
│  ┌──────────┐  ┌──────────┐   │
│  │  linter  │  │  pytest  │   │
│  │ (pre-    │  │ (tests,  │   │
│  │  commit) │  │  migra-  │   │
│  └──────────┘  │  tions)  │   │
│       │        └────┬─────┘   │
│       └──────────┬──┘         │
│                  ▼            │
│          ┌──────────────┐     │
│          │  docker      │     │
│          │  (build &    │     │
│          │  push to     │     │
│          │  ghcr.io)    │     │
│          └──────┬───────┘     │
└─────────────────┼──────────────┘
                  │ workflow_run
                  ▼
┌────────────────────────────────┐
│  CD (GitHub Actions)           │
│  Deploy Infrastructure         │
│                                │
│  0. Gate on docker success     │
│  1. Verify image manifests     │
│  2. Inject Bitwarden secrets   │
│  3. Connect to Tailscale       │
│  4. Write SSH key              │
│  5. Run Ansible playbook       │
│     ┌────────────────────┐     │
│     │ site.yml            │     │
│     │  ┌──────────────┐   │     │
│     │  │ deploy_      │   │     │
│     │  │ application  │   │     │
│     │  │ .yml         │   │     │
│     │  └──────┬───────┘   │     │
│     └─────────┼───────────┘     │
└───────────────┼─────────────────┘
                │ Coolify API
                ▼
┌────────────────────────────────┐
│  Coolify (on Hetzner VPS)      │
│                                │
│  - Receives env vars via API   │
│  - Pulls docker-compose.coolify│
│    .yml from the branch head   │
│  - Pulls immutable SHA-tagged  │
│    images from ghcr.io         │
│  - Starts the container stack  │
│  - Containers resolve runtime  │
│    secrets from Bitwarden via  │
│    BWS CLI at startup          │
└────────────────────────────────┘
```

---

## Stage 1 — Continuous Integration (CI)

**Workflow file:** `.github/workflows/ci.yml`

**Trigger:** Push or PR to `main`/`staging` (excluding `docs/` paths). The
`docker` job runs only on push events and only when the `changes` filter
reports `build_and_deploy` (application or deployment inputs). Docs-only
pushes do not start CI at all; README/test-only pushes run CI but cannot
reach the Docker or deploy jobs.

### Jobs

| Job | Purpose |
|-----|---------|
| `changes` | Detects whether application or deployment files changed (`dorny/paths-filter`) |
| `linter` | Runs pre-commit hooks (ruff, djlint, mypy, etc.) |
| `migrations` | Checks for missing migrations, runs `migrate`, and runs the health endpoint test |
| `docker` | Builds and pushes immutable images to GitHub Container Registry on push when `build_and_deploy` is true |

The full `pytest` suite is not run by CI yet; the health endpoint contract is
covered by a targeted test in the `migrations` job.

### Image tagging

All images are pushed to a single repository per component under
`ghcr.io/baldwinboy/`:

| Image | Tags |
|-------|------|
| `neuromancers-network` | `{sha}`, plus `latest`/`staging` for compatibility |
| `neuromancers-network-postgres` | `postgres-{tree-sha}`, `{sha}`, plus `latest`/`staging` for compatibility |

Deployments use **immutable tags**, not branch tags:

- `DOCKER_TAG` is the 40-character commit SHA.
- `POSTGRES_TAG` is a content tag derived from
  `compose/production/postgres` (`postgres-{git-tree-sha}`), so app-only
  deploys do not recreate the database container.

`docker-compose.coolify.yml` requires both variables:

```yaml
image: ghcr.io/baldwinboy/neuromancers-network:${DOCKER_TAG:?...}
image: ghcr.io/baldwinboy/neuromancers-network-postgres:${POSTGRES_TAG:?...}
```

The branch tags remain for rollback compatibility, but they are not used by
the deployment path.

---

## Stage 2 — Continuous Deployment (CD)

**Workflow file:** `.github/workflows/deploy.yml`

**Trigger:** Successful completion of the `CI` workflow on `main` or
`staging` (`workflow_run` event). `workflow_run` uses the deploy workflow
from the default branch (`main`), so changes to `deploy.yml` only take effect
on staging after they reach `main`.

### Steps

1. **Gate** — Reads the triggering CI run and requires the `docker` job to
   have concluded `success`. If it was skipped or missing, the deployment
   job is skipped. This prevents a deploy without a new image.
2. **Checkout** — Checks out the exact commit SHA from CI.
3. **Postgres tag** — Computes `POSTGRES_TAG` from the target commit.
4. **Manifest gate** — Confirms the app `{sha}` image and postgres
   `postgres-{tree-sha}` image exist in GHCR. Fails before Ansible if
   either is missing.
5. **Ansible install** — Installs Ansible.
6. **BWS CLI install** — Downloads the latest Bitwarden Secrets Manager
   CLI binary from GitHub releases.
7. **BWS validation** — Confirms `BWS_ACCESS_TOKEN` is set in GitHub
   environment secrets.
8. **Secret injection** — Uses `bws secret list` + `jq` to extract
   required secrets from Bitwarden. Masks and exports them as step
   outputs.
9. **Tailscale connect** — Joins the GitHub runner to the tailnet using
   OAuth credentials from Bitwarden.
10. **SSH key setup** — Writes the Hetzner SSH private key for Ansible
    connectivity.
11. **Ansible Galaxy install** — Installs required collections.
12. **Ansible playbook run** — Executes `infra/playbooks/site.yml` under
    `bws run` with `git_branch`, `git_commit_sha`, `git_repository`,
    `git_environment`, `postgres_tag`, `require_health_revision`, and
    `verify_source_sha`.

A `workflow_dispatch` entry point supports image-only rollback. It validates
the SHA, branch, and environment; checks the image manifests; and does not
require the Compose source revision to equal the rolled-back image SHA.

### Environment awareness

The deploy workflow maps branches to GitHub environments:

| Branch | GitHub Environment | `git_environment` var |
|--------|-------------------|----------------------|
| `main` | `production` | `production` |
| `staging` | `staging` | `staging` |

Each GitHub environment has its own `BWS_ACCESS_TOKEN` secret, allowing
separate Bitwarden projects for production and staging secrets.

---

## Stage 3 — Ansible orchestration

**Playbook:** `infra/playbooks/site.yml`

### Roles / imported playbooks

| Playbook | Function |
|----------|----------|
| `setup_coolify.yml` | Installs & configures Coolify, Tailscale, CrowdSec, Fail2Ban, UFW firewall |
| `deploy_application.yml` | Creates/updates the `neuromancers_network` application in Coolify via API |
| `schedule_maintenance.yml` | Sets up cron jobs (session cleanup, etc.) |

### Coolify API interaction

The `deploy_application.yml` playbook:

1. Validates the SHA, branch, environment, and postgres tag.
2. Checks Coolify API health and required tokens.
3. Lists and identifies the host server.
4. Creates the `neuromancers` project if missing.
5. Creates or reuses the `neuromancers` environment.
6. Creates or reuses the `neuromancers_network` application with
   `build_pack: dockercompose` pointing at `docker-compose.coolify.yml`.
7. PATCHes `git_branch` and disables Coolify auto-deploy.
8. Pushes `BWS_ACCESS_TOKEN`, `DOCKER_TAG`, `POSTGRES_TAG`, `TS_APP_DOMAIN`,
   `TS_PAAS_DOMAIN`, `TAILSCALE_TAG`, `TS_OAUTH_CLIENT_ID`, and
   `TS_OAUTH_CLIENT_SECRET` as Coolify env vars.
9. Triggers the deployment and asserts that Coolify returned a deployment UUID.
10. Verifies the Coolify source SHA, running image tags, and `/api/health`
    revision after deployment.

Coolify resolves the Compose file from `git_branch` (the branch head). Its
stored `git_commit_sha` is a record of the last deployed commit, not a pin.
Do not PATCH `git_commit_sha` or `git_repository` to control a deployment.

---

## Stage 4 — Coolify deployment

Coolify runs on the Hetzner VPS behind Tailscale (not publicly
accessible). It manages the Docker Compose stack defined in
`docker-compose.coolify.yml`.

### Stack services

| Service | Image | Function |
|---------|-------|----------|
| `tsdproxy` | `almeidapaulopt/tsdproxy:dev` | Tailscale proxy/VIP services for the stack |
| `django` | `ghcr.io/baldwinboy/neuromancers-network:${DOCKER_TAG}` | Gunicorn WSGI server on port 5000 |
| `postgres` | `ghcr.io/baldwinboy/neuromancers-network-postgres:${POSTGRES_TAG}` | PostgreSQL 18 |
| `redis` | `docker.io/redis:8.8` | Message broker / cache |
| `celeryworker` | `ghcr.io/baldwinboy/neuromancers-network:${DOCKER_TAG}` | Celery async task worker |
| `celerybeat` | `ghcr.io/baldwinboy/neuromancers-network:${DOCKER_TAG}` | Celery periodic task scheduler |
| `gatus` | `ghcr.io/twin/gatus:stable` | Uptime monitoring, status page and alerts |

### Runtime secret resolution

Ansible pushes only `BWS_ACCESS_TOKEN`, `DOCKER_TAG`, `POSTGRES_TAG`,
`TS_APP_DOMAIN`, `TS_PAAS_DOMAIN`, `TAILSCALE_TAG`, `TS_OAUTH_CLIENT_ID`,
and `TS_OAUTH_CLIENT_SECRET` to Coolify.
All other runtime secrets must be **manually added** to the Coolify
application by a developer after first creation.

See [Operator Guide — First deployment](operator-guide.md#first-deployment)
for the manual setup procedure.

On subsequent deploys, Ansible refreshes secrets that already exist
in Coolify by matching keys from Bitwarden against the Coolify
environment variables.

---

## Stage 5 — Application startup

The Django container entrypoint runs sequentially:

1. Injects Bitwarden secrets via `bws run`.
2. Sets `DATABASE_URL` from `POSTGRES_*` env vars.
3. Waits for PostgreSQL to become available (`wait-for-it`).
4. Executes the command (`/start`).

The `/start` script runs:

1. `manage.py migrate --noinput` — Applies pending DB migrations.
2. `manage.py ensure_superuser` — Ensures the bootstrap superuser exists.
3. `manage.py collectstatic --noinput` — Collects static files.
4. `gunicorn config.wsgi` — Starts the WSGI server.

The image is built with `GIT_COMMIT_SHA` as an environment variable.
`/api/health` returns:

```json
{"status": "ok", "revision": "<commit-sha>"}
```

After deployment Ansible asserts that `revision` equals the deployed SHA and
that the running Django/Celery/Postgres containers use the expected tags.

---

## Secrets architecture

```
GitHub Environments
  └── BWS_ACCESS_TOKEN (per env: production / staging)
        │
        ▼
Bitwarden Secrets Manager
  ├── Infrastructure secrets (Tailscale, Hetzner SSH, Coolify API)
  ├── Runtime secrets (DB creds, Redis URL, Django secret key, etc.)
  │     │
  │     ├── GitHub Actions CD (via bws secret list + jq)
  │     └── Developer manually adds to Coolify UI
  │           │
  │           ▼
  │         Coolify application env vars
  │           │
  │           ▼
  │         Application containers (receive secrets at startup)
  │
  └── BWS_ACCESS_TOKEN → pushed to Coolify by Ansible (along with DOCKER_TAG,
        POSTGRES_TAG, TS_*_DOMAIN, and TAILSCALE_TAG)
```

---

## Key architectural decisions

- **Single VPS + Coolify** rather than Kubernetes — appropriate for
  current scale and operational complexity.
- **Ansible over Terraform** for server state — simpler to bootstrap
  and maintain for a single host.
- **Bitwarden over GitHub Secrets** for most secrets — centralised
  secret management that works both in CI and at runtime.
- **Tailscale over public IP** for Coolify access — Coolify dashboard
  is not exposed to the internet.
- **Docker Compose over raw Docker** — declarative stack definition
  that Coolify understands natively.
