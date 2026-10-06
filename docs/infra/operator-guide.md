# Operator Guide

## Deployment model

- `CI` is the gate.
- `Deploy Infrastructure` runs only from a successful `workflow_run` of `CI`.
- GitHub Actions joins Tailscale before reaching Coolify.
- Ansible owns host mutation.
- Coolify owns application deployment for the compose-native stack.
- Ansible pushes only `BWS_ACCESS_TOKEN`, `DOCKER_TAG`, the `TS_*_DOMAIN` keys, and `TAILSCALE_TAG` to Coolify.
- Developers manually add all other secrets from Bitwarden to the Coolify application after first creation.

## Secret model

- Source of truth for infrastructure and runtime secrets is Bitwarden Secrets Manager.
- GitHub stores only `BWS_ACCESS_TOKEN` (the Bitwarden machine access token).
- Ansible pushes `BWS_ACCESS_TOKEN`, `DOCKER_TAG`, the `TS_*_DOMAIN` keys, and `TAILSCALE_TAG` to Coolify during deployment.
- All other secrets must be manually added to the Coolify application by a developer.
- The filter for which secrets to push is NOT in Ansible — it is a manual developer action.
- Workflows must read secrets with `bws secret list` and filter by `.key`.
- There is no API in `bws` to fetch by key name directly. Use list + jq filtering.

## First deployment

After Ansible creates the Coolify application for the first time:

1. Log into the Coolify dashboard over Tailscale.
2. Navigate to the `neuromancers_network` application.
3. Go to the **Environment variables** tab.
4. Manually add all desired secrets from Bitwarden. These may be stub values initially.
5. Only secrets present in Coolify will be refreshed on subsequent Ansible deploys.
6. The application must be restarted after adding secrets (Coolify does this automatically on save).

This step cannot be automated because the set of secrets each developer wants is a manual decision.

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
- `TAILSCALE_TAG`

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

- The Hetzner host must join the tailnet with `tag:<environment>-coolify-ci`, i.e. `tag:production-coolify-ci`.
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

## Coolify lockdown (tailnet-only)

The Coolify control plane is private to the tailnet:

- Ansible (`tasks/configure_firewall.yml`) never opens ports `8000`
  (dashboard/API), `6001` (real-time) or `6002` (terminal) to the public
  internet, and deletes any legacy public allow rules on every run.
- Those ports are reachable only over Tailscale, either at the host's
  tailnet IP (`http://<tailscale-ip>:8000`) or through the Serve hostname
  (`https://<stage>-paas.<tailnet>.ts.net`).
- Docker publishes these ports through the FORWARD chain, so Ansible adds
  matching `ufw route` rules scoped to `tailscale0`, on top of the
  `ufw-docker` default-deny for public traffic.

Complete the following instance hardening once, in the Coolify UI:

1. **Settings → Configuration → Advanced**: enable API access only if
   needed and set **Allowed IPs for API Access** to `100.64.0.0/10`
   (the Tailscale CGNAT range).
2. **Settings → Authentication**: disable **Registration Allowed**.
3. Enable two-factor authentication for every account with elevated access.
4. Confirm the dashboard is not reachable from outside the tailnet:
   `curl -m 5 http://<public-ip>:8000/api/v1/health` must fail, while
   `curl http://<tailscale-ip>:8000/api/v1/health` returns `200`.

## Normal deployment flow

1. Push reviewed changes to `main` or `staging`.
2. Wait for `CI` to pass.
3. Confirm `Deploy Infrastructure` starts automatically.
4. Confirm Ansible converge succeeds.
5. Confirm the Coolify application has the secrets needed for runtime (added manually after first deploy).
6. Confirm deployment finishes successfully.
7. Confirm smoke checks pass.

## Deployment Workflow

The deployment pipeline is a hybrid of automated Ansible provisioning and
manual Coolify platform configuration. The complete flow:

### Step 1 — Ansible: Infrastructure Provisioning (automated)
Playbook `setup_coolify.yml` installs and configures:
- Coolify (PaaS dashboard)
- Tailscale (private networking)
- CrowdSec (WAF / IPS)
- Fail2Ban with SSH hardening
- UFW firewall rules
- SSH key generation for Coolify host server

### Step 2 — Developer: Enable Coolify API (manual)
1. Log into Coolify dashboard over Tailscale
2. Go to Settings → API → enable the API
3. Copy the API token shown on-screen
4. Store it in Bitwarden Secrets Manager as `COOLIFY_API_TOKEN`
   (This step CANNOT be automated — Coolify requires interactive login)

### Step 3 — Ansible: Server Reachability (automated)
Playbook `configure_coolify_api.yml`:
- Verifies Coolify API health
- Generates an ed25519 SSH key for the Coolify host
- Registers the key with Coolify via the API
- Validates the host server is reachable from Coolify

### Step 4 — Developer: Enable Traefik Access Logs for CrowdSec (manual)
1. In Coolify, navigate to the Traefik proxy service
2. Under the `command` field, append:
```
- '--accesslog=true'
- '--accesslog.format=json'
```
3. Under `labels`, append:
```
- crowdsec.enable=true
- crowdsec.labels.type=traefik
```
4. Under `ports`, remove port `8080`.

(This CANNOT be automated initially, as the compose file will not be available until everything is valid)

### Step 5 — Developer: Generate Deploy-Only API Token (manual)
1. In Coolify, go to Settings → API → generate a new token
2. Grant only the `deploy` permission
3. Store in Bitwarden as `COOLIFY_DEPLOY_TOKEN`
4. Set `COOLIFY_DEPLOY_TOKEN` in GitHub Environment secrets
(Used by `deploy_application.yml` and GitHub Actions)

### Summary Diagram
[Ansible] → installs Coolify + Tailscale + CrowdSec + Fail2Ban
 ↓
[Manual] → enable Coolify API, copy token
 ↓
[Ansible] → SSH key generation, server reachability validation
 ↓
[Manual] → configure Traefik access logs for CrowdSec
 ↓
[Manual] → generate deploy-only API token for GitHub Actions
 ↓
[Ansible] → deploy_application.yml: project / env / app creation