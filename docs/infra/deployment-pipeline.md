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
│  1. Inject Bitwarden secrets   │
│  2. Connect to Tailscale       │
│  3. Write SSH key              │
│  4. Run Ansible playbook       │
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
│    .yml from git commit        │
│  - Pulls Docker images from    │
│    ghcr.io with correct tag    │
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
`docker` job additionally requires the `changes` filter to report
application changes and runs only on push events.

### Jobs

| Job | Purpose |
|-----|---------|
| `changes` | Detects whether application/build files changed (`dorny/paths-filter`) |
| `linter` | Runs pre-commit hooks (ruff, djlint, mypy, etc.) |
| `migrations` | Checks for missing migrations (`makemigrations --check`) and runs `migrate` |
| `docker` | Builds and pushes images to GitHub Container Registry, only when app files changed and only on push |

The test suite exists (`pytest`) but is not currently run by CI.

### Image tagging

All images are pushed to a single repository per component under
`ghcr.io/baldwinboy/`, with environment-specific tags:

| Branch | Django image tag | Postgres image tag |
|--------|-----------------|-------------------|
| `main` | `neuromancers-network:latest` | `neuromancers-network-postgres:latest` |
| `main` | `neuromancers-network:{sha}` | `neuromancers-network-postgres:{sha}` |
| `staging` | `neuromancers-network:staging` | `neuromancers-network-postgres:staging` |
| `staging` | `neuromancers-network:{sha}` | `neuromancers-network-postgres:{sha}` |

The `docker-compose.coolify.yml` file uses the `DOCKER_TAG` variable
(resolved by Coolify at deploy time) to select the correct tag.

---

## Stage 2 — Continuous Deployment (CD)

**Workflow file:** `.github/workflows/deploy.yml`

**Trigger:** Successful completion of the `CI` workflow on `main` or
`staging` (`workflow_run` event).

### Steps

1. **Checkout** — Checks out the exact commit SHA from CI.
2. **Ansible install** — Installs Ansible 13.6.x.
3. **BWS CLI install** — Downloads the latest Bitwarden Secrets Manager
   CLI binary from GitHub releases.
4. **BWS validation** — Confirms `BWS_ACCESS_TOKEN` is set in GitHub
   environment secrets.
5. **Secret injection** — Uses `bws secret list` + `jq` to extract
   required secrets from Bitwarden. Masks and exports them as step
   outputs.
6. **Tailscale connect** — Joins the GitHub runner to the tailnet using
   OAuth credentials from Bitwarden.
7. **SSH key setup** — Writes the Hetzner SSH private key for Ansible
   connectivity.
8. **Ansible Galaxy install** — Installs required collections.
9. **Ansible playbook run** — Executes `infra/playbooks/site.yml` under
   `bws run` with `git_branch`, `git_commit_sha`, `git_repository`, and
   `git_environment` extra vars.

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

1. Checks Coolify API health.
2. Lists and identifies the host server.
3. Creates the `neuromancers` project if missing.
4. Creates or reuses the `neuromancers` environment.
5. Creates or reuses the `neuromancers_network` application with
   `build_pack: dockercompose` pointing at `docker-compose.coolify.yml`.
6. Pushes `BWS_ACCESS_TOKEN`, `DOCKER_TAG`, `TS_APP_DOMAIN`, `TS_PAAS_DOMAIN`,
   `TAILSCALE_TAG`, `TS_OAUTH_CLIENT_ID`, and `TS_OAUTH_CLIENT_SECRET` as
   Coolify env vars.

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
| `postgres` | `ghcr.io/baldwinboy/neuromancers-network-postgres:${DOCKER_TAG}` | PostgreSQL 18 |
| `redis` | `docker.io/redis:8.8` | Message broker / cache |
| `celeryworker` | `ghcr.io/baldwinboy/neuromancers-network:${DOCKER_TAG}` | Celery async task worker |
| `celerybeat` | `ghcr.io/baldwinboy/neuromancers-network:${DOCKER_TAG}` | Celery periodic task scheduler |
| `prometheus` | `docker.io/prom/prometheus:main-distroless` | Metrics collection and healthchecks |

### Runtime secret resolution

Ansible pushes only `BWS_ACCESS_TOKEN`, `DOCKER_TAG`, `TS_APP_DOMAIN`,
`TS_PAAS_DOMAIN`, `TAILSCALE_TAG`, `TS_OAUTH_CLIENT_ID`, and
`TS_OAUTH_CLIENT_SECRET` to Coolify.
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
        TS_*_DOMAIN, and TAILSCALE_TAG)
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
