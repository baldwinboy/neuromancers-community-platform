# Operator Guide

## Deployment model

- `CI` is the gate.
- `Deploy Infrastructure` runs only from a successful `workflow_run` of `CI`.
- GitHub Actions joins Tailscale before reaching Coolify.
- Ansible owns host mutation.
- Coolify owns application deployment for the compose-native stack.
- Coolify should hold only the Bitwarden access token needed for runtime secret resolution.
- Each application container should resolve its own runtime secrets from Bitwarden at startup via the BWS CLI.

## Secret model

- Source of truth for infrastructure and runtime secrets is Bitwarden Secrets Manager.
- GitHub stores only `BWS_ACCESS_TOKEN` (the Bitwarden machine access token).
- Workflows must read secrets with `bws secret list` and filter by `.key`.
- There is no API in `bws` to fetch by key name directly. Use list + jq filtering.

## GitHub environments

Create two environments in GitHub:

- `production` for `main`
- `staging` for `staging`

Configure in the GitHub UI:

- Required reviewers for `production`
- Branch restriction so only `main` can deploy to `production`
- Branch restriction so only `staging` can deploy to `staging`
- `BWS_ACCESS_TOKEN` in each environment

## Required deploy-time secrets

GitHub environments must include:

- `BWS_ACCESS_TOKEN`

Bitwarden must include at least:

- `TS_OAUTH_CLIENT_ID`
- `TS_OAUTH_CLIENT_SECRET`
- `HETZNER_SSH_HOST`
- `HETZNER_SSH_PRIVATE_KEY`
- `HETZNER_SSH_USER`
- `HETZNER_SSH_KNOWN_HOSTS`
- `COOLIFY_API_URL`
- `COOLIFY_API_TOKEN`
- `COOLIFY_APPLICATION_UUID`
- `APP_HEALTHCHECK_URL`
- `COOLIFY_PUBLIC_PROBE_URL`
- The runtime application keys listed in [Coolify Env Mapping](../infra/coolify-env-mapping.md)

Coolify must receive:

- `BWS_ACCESS_TOKEN`

## Bitwarden CLI behavior and usage

- `bws secret list` returns a JSON array of objects with `key` and `value`.
- To execute a command with all secrets injected, use `bws run -- '<command>'`.
- To extract a specific subset by key, filter from `bws secret list` output.

Example extraction pattern:

```bash
bws secret list \
	| jq -r '.[] | select(.key=="HETZNER_SSH_USER") | .value'
```

## Tailscale setup

- The Hetzner host must join the tailnet with `tag:coolify-host`.
- GitHub Actions joins with `tag:ci`.
- Coolify must be addressed by Tailscale IP or MagicDNS hostname.
- Do not expose the Coolify dashboard or API to the public internet.
- Do not enable Tailscale Funnel for Coolify.

## Allowed operator actions

- Merge to `main` or `staging` after review.
- Trigger or re-run the GitHub deploy workflow.
- Reach Coolify over Tailscale for read-only inspection or emergency admin actions.
- Rotate GitHub environment secrets.
- Rotate Coolify API credentials.
- Rotate Tailscale credentials.
- Run the Ansible playbook from CI as the canonical reconciliation path.

## Forbidden operator actions

- Do not make ad hoc host changes over SSH as the normal path.
- Do not edit live application secrets manually in Coolify unless handling an incident.
- Do not expose Coolify publicly.
- Do not use `bootstrap.sh` as the standard deployment path.
- Do not store live credentials in tracked `.env` files.

## How to reach Coolify

1. Join the tailnet with an approved operator device.
2. Open the private Coolify hostname or Tailscale IP from `COOLIFY_API_URL`.
3. Confirm the public probe URL still fails from outside the tailnet.

## Normal deployment flow

1. Push reviewed changes to `main` or `staging`.
2. Wait for `CI` to pass.
3. Confirm `Deploy Infrastructure` starts automatically.
4. Confirm Ansible converge succeeds.
5. Confirm the Coolify application has the Bitwarden token needed for runtime secret resolution.
6. Confirm deployment finishes successfully.
7. Confirm smoke checks pass.

## IaC completion checklist (audit: 2026-05-07)

1. Fix `Deploy Infrastructure` workflow structure in `.github/workflows/deploy.yml`.
2. Wire all Ansible variables explicitly (inventory and playbook vars), rather than relying on implicit environment variable expansion.
3. Remove `--tags deploy` or add explicit `deploy` tags to required tasks so converge actually runs.
4. Decide and document the Coolify token-injection path for runtime containers.
5. Add a preflight secret presence check against required Bitwarden keys before any deploy mutation.
6. Implement container-side secret bootstrap in each production image or shared entrypoint.
7. Replace non-routable defaults (`http://django:8000/health/`) with externally valid health endpoints for host-level smoke checks.
8. Verify container name assertions in smoke checks match Coolify runtime names (or use label-based checks).
9. Pin Ansible collection versions in `infra/galaxy/requirements.yml` for reproducible deploys.
10. Run one full staging dry run from CI and record evidence (workflow URL, task summary, smoke output) before production enablement.