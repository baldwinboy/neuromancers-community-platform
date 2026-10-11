# Exposing the Django App on a Custom Domain

> **Status:** Design guide / decision record. This document proposes changes; it
> does not apply them. The only files it edits are itself and
> [`index.md`](index.md).

This guide explains, in plain language and then in technical detail, the viable
ways to put **NEUROMANCERS Network** behind one or more public domain names
(for example `network.neuromancers.org.uk`), and gives a **diff-level plan** for
each option.

---

## 1. Who this is for

- **Non-technical readers** can read Sections 2–4 (the "plain language" parts),
  the solution overview table in Section 6, and the recommendation in Section 7.
- **Technical readers** should also read Sections 5–12 for the design rationale,
  exact configuration and diff-level plans, risks, and verification steps.

---

## 2. Plain-language summary

Today the application only lives **inside a private network** (a "tailnet" run by
Tailscale). Only devices you have approved can reach it. We now want the public
internet to reach it at a friendly address such as `network.neuromancers.org.uk`.

Think of it like a shop:

- The **domain name** is the street address customers type in.
- **DNS** is the postal service that translates that address into the building's
  real location (the server's IP address).
- A **certificate (TLS/HTTPS)** is the padlock that proves to visitors they are
  talking to the real shop and not an impersonator.
- A **reverse proxy** is the doorman at the entrance who reads which shop name the
  visitor asked for and walks them to the right counter (our Django app).
- A **CDN/WAF** (Cloudflare and friends) is a security guard and a chain of local
  depots: it can stand in front of the shop, absorb attacks, and hand visitors a
  nearby copy of the shopfront. It can also **hide the building's real address**
  so nobody can walk straight up to it.
- A **tunnel** is a private service corridor from the security guard to the shop,
  so the shop front door never has to be unlocked to the street.

**The core choice** is whether the shop's real address is public (simpler, still
safe) or hidden behind a security guard/depot (a bit more machinery, strictly
more private). Everything else — which company hosts the address, how the
padlock is issued, and how many names point at once — can be chosen
independently because we deliberately keep those pieces swappable.

**Cost:** every recommended option runs on free tiers (Let's Encrypt
certificates, Cloudflare free, Tailscale free). The only paid options are
optional add-ons we do **not** need at this scale.

---

## 3. Goals and constraints

| Goal | Requirement |
|------|-------------|
| Public access | Reach the Django app over HTTPS at a custom domain |
| Multiple domains | Several domains/aliases can point at the app |
| Provider-neutral | IONOS, Cloudflare, GoDaddy, Hetzner, etc. are interchangeable |
| Security | TLS everywhere, WAF/IPS, private admin/control planes stay private |
| Origin privacy | Prefer the server IP hidden, but not a hard requirement |
| Cost | £0 preferred; small paid add-ons only if materially better |
| Maintainability | Domain changes are configuration, not code rewrites |

**Non-goals:** exposing the Coolify dashboard, `tsdproxy`, or Gatus publicly.
Those stay tailnet-only.

---

## 4. Glossary

| Term | Meaning |
|------|---------|
| **DNS** | Service that maps a domain name to a server IP (A/AAAA records) or to another name (CNAME). |
| **A / AAAA record** | DNS record pointing a name to an IPv4 / IPv6 address. |
| **CNAME record** | DNS record pointing a name to another name. |
| **TLS / HTTPS** | Encryption + identity. Issued by a Certificate Authority (e.g. Let's Encrypt). |
| **Let's Encrypt (LE)** | Free, automated certificate authority. |
| **HTTP-01 challenge** | Proving domain ownership by serving a file on public port 80. |
| **DNS-01 challenge** | Proving ownership by adding a temporary DNS record. Needed for wildcards and when port 80 is closed. |
| **Wildcard certificate** | One certificate covering `*.example.com` (all subdomains). Requires DNS-01. |
| **Reverse proxy** | Server that receives public traffic and forwards it to the app. Coolify uses Traefik (default) or Caddy. |
| **CDN / WAF** | Content Delivery Network / Web Application Firewall. Cloudflare is the common example. |
| **Tunnel** | Outbound-only connection from the server to a provider, so no inbound ports are needed (e.g. Cloudflare Tunnel). |
| **Coolify** | The PaaS that deploys and manages our Docker stack on the Hetzner VPS. |
| **Tailscale / tailnet** | Private encrypted network connecting our approved devices and servers. |
| **tsdproxy** | Tailscale Docker proxy that currently exposes the app privately on the tailnet. |
| **Gatus** | Uptime monitoring / status page (tailnet-only). |

---

## 5. Design rationale (why the recommendation is what it is)

1. **Coolify already runs the edge proxy (Traefik).** It supports unlimited
   domains, comma-separated multi-domain configuration, automatic Let's Encrypt
   certificates, custom middlewares (rate limiting, security headers, redirects)
   and dynamic configuration. Reusing it means the fewest moving parts.
2. **DNS-01 is the provider-neutral unlock.** Let's Encrypt's DNS-01 challenge is
   implemented by the Lego library, which supports IONOS, Cloudflare, Hetzner,
   GoDaddy, Gandi, Namecheap and many more. It enables wildcards, works with port
   80 closed, and coexists with a CDN in front. HTTP-01 works too but is less
   flexible.
3. **The front security layer must be optional.** Hiding the origin IP is
   desirable but not mandatory, so we design so a CDN/tunnel can be added or
   removed without changing the application.
4. **tsdproxy custom domains are the wrong tool.** TSDProxy's custom-domain
   feature supports **only Cloudflare** for DNS and requires editing
   `infra/tsdproxy/config/critical.yml` per domain, so every domain change is a
   code change and every migration is a rewrite. It is excellent for **private**
   tailnet access, which we keep — just not for the public endpoint.

---

## 6. Solution catalog

| # | Solution | Cost | Origin IP | Wildcard | Provider portability | Maintainability |
|---|----------|------|-----------|----------|----------------------|-----------------|
| A | Coolify Traefik + Let's Encrypt **HTTP-01** | £0 | Exposed | No | Any (DNS-only records) | ★★★★ |
| B | Coolify Traefik + Let's Encrypt **DNS-01** | £0 | Exposed | Yes | Any (Lego providers) | ★★★★ |
| C | Coolify **Caddy** + Let's Encrypt | £0 | Exposed | Yes | Any | ★★ |
| D | **Self-managed edge** (Caddy/Traefik) in compose | £0 | Exposed | Yes | Any | ★★ |
| E | **Cloudflare Tunnel** (`cloudflared`) | £0 | **Hidden, no open ports** | Yes | Cloudflare DNS | ★★★ |
| F | **Cloudflare proxied DNS** + Origin/LE cert | £0 | Hidden (443 open) | Yes (DNS-01) | Cloudflare DNS | ★★★ |
| G | **Tailscale Funnel** | £0 | Hidden, no open ports | No | `*.ts.net` only | ★★ |
| H | External load balancer / second VPS | ~€5.5+/mo | Hidden | n/a | Any | ★ |

- **A** is the simplest possible starting point.
- **B is the recommended baseline** (same simplicity, more capability).
- **E is the recommended hardening layer** when origin privacy matters.
- **G and H are not recommended** for the public multi-domain requirement and are
  documented only for completeness.

---

## 7. Recommendation and decision guide

### Recommended default

> **Coolify's Traefik (B) with Let's Encrypt DNS-01, domains supplied as data,
> and an optional Cloudflare layer in front (E for "no open ports", or F for
> "hidden IP with only 443 open").**

### Decision guide

**Step 1 — Does the origin IP need to be hidden?**
- No → use **A** (specific hosts) or **B** (wildcard/port-80-closed). Exposed
  origin is protected by TLS + CrowdSec + Fail2Ban.
- Prefer hidden, not mandatory → use **B**, then optionally add **E** or **F**.
- Must hide → use **E** (no inbound ports at all) or **F** (only 443 open).

**Step 2 — Certificate challenge**
- Specific hostnames and an open port 80 → **HTTP-01** is fine (A).
- Wildcards, or port 80 closed, or a CDN/tunnel in front → **DNS-01** (B).

**Step 3 — Who owns the edge?**
- Prefer least machinery and vendor support → **Coolify Traefik** (A/B).
- Prefer the Caddyfile model → **Coolify Caddy** (C).
- Want the edge fully declared in this repo → **self-managed** (D), accepting
  that it displaces Coolify's proxy on ports 80/443.
- Want maximum origin privacy → **Cloudflare Tunnel** (E).

**Step 4 — How should multiple domains behave?**
- Same content on all names → add every name to Django `ALLOWED_HOSTS`,
  `CSRF_TRUSTED_ORIGINS`, and Wagtail Sites.
- One canonical name, others redirect → proxy-level 301 to canonical (preferred
  for SEO); one Wagtail Site.
- A mix → decide per domain.

---

## 8. Cross-cutting changes (apply to every solution)

These changes are needed regardless of which ingress you choose. Full diffs are
shown once here and referenced by the per-solution plans.

### 8.1 Domain list as data

Add two new secrets to **Bitwarden Secrets Manager**:

- `APP_DOMAINS` — comma-separated FQDNs, canonical **first**
  (e.g. `network.neuromancers.org.uk,network.example.com`).
- `CANONICAL_DOMAIN` — the single preferred name used for redirects and Wagtail
  (e.g. `network.neuromancers.org.uk`).

### 8.2 Django settings

`config/settings/production.py` — replace the placeholder `CUSTOM_DNS` with an
env-driven domain list and add the currently-missing CSRF origins.

```diff
 SERVER_HOST = env("HETZNER_SSH_HOST", default=None)
-CUSTOM_DNS = env("CUSTOM_DNS", default="1.1.1.1")
+CUSTOM_DNS = env("CUSTOM_DNS", default=None)
 TS_APP_DOMAIN = env("TS_APP_DOMAIN", default=None)
-DYNAMIC_ALLOWED_HOSTS = [SERVER_HOST, CUSTOM_DNS, TS_APP_DOMAIN]
+# Public custom domains, canonical first. Data, not code.
+APP_DOMAINS = [d.strip() for d in env.list("APP_DOMAINS", default=[]) if d.strip()]
+CANONICAL_DOMAIN = env(
+    "CANONICAL_DOMAIN",
+    default=(APP_DOMAINS[0] if APP_DOMAINS else None),
+)
+DYNAMIC_ALLOWED_HOSTS = [SERVER_HOST, CUSTOM_DNS, TS_APP_DOMAIN, *APP_DOMAINS]
 DJANGO_ALLOWED_HOSTS = [
     *env.list(
         "DJANGO_ALLOWED_HOSTS",
-        default=["localhost", "django", "127.0.0.1", "neuromancers.org.uk"],
+        default=["localhost", "django", "127.0.0.1"],
     ),
 ]
 ALLOWED_HOSTS = [
     *DJANGO_ALLOWED_HOSTS,
     *[
         host
         for host in DYNAMIC_ALLOWED_HOSTS
         if host and host not in DJANGO_ALLOWED_HOSTS
     ],
     *[host for host in ("localhost", "127.0.0.1") if host not in DJANGO_ALLOWED_HOSTS],
 ]
+
+# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-trusted-origins
+CSRF_TRUSTED_ORIGINS = [
+    *[f"https://{d}" for d in APP_DOMAINS],
+    *env.list("CSRF_TRUSTED_ORIGINS", default=[]),
+]
```

> **Django 4+** requires `CSRF_TRUSTED_ORIGINS` for form POSTs behind a proxy on
> a custom domain. Without it, logins and most forms fail with a CSRF error.

> **Wagtail multi-domain:** Wagtail matches the incoming host against `Site`
> records. For "all domains serve the same app", create a `Site` per hostname
> (or add a small middleware that treats listed `APP_DOMAINS` as the canonical
> site). For "redirect to canonical", keep one Site and let the proxy 301 the
> aliases. Set `WAGTAILADMIN_BASE_URL` to `https://<CANONICAL_DOMAIN>`.

### 8.3 Environment documentation

`.env.example` — document the new keys (documentation only; no secrets).

```diff
 # === Django Core =============================================================
 
 DJANGO_SETTINGS_MODULE=config.settings.local
@@
 DJANGO_ALLOWED_HOSTS=.localhost,127.0.0.1,0.0.0.0
+# Comma-separated public custom domains, canonical first.
+APP_DOMAINS=network.neuromancers.org.uk
+# Single preferred domain for redirects and Wagtail.
+CANONICAL_DOMAIN=network.neuromancers.org.uk
 HETZNER_SSH_HOST=
```

### 8.4 Inventory variables

`infra/inventory/hosts.yml` — surface the secrets as Ansible vars (mirrors the
existing pattern for other Bitwarden-sourced values).

```diff
     tailscale_oauth_client_id: "{{ lookup('ansible.builtin.env', 'TS_OAUTH_CLIENT_ID', default=undef()) }}"
     tailscale_oauth_client_secret: "{{ lookup('ansible.builtin.env', 'TS_OAUTH_CLIENT_SECRET', default=undef()) }}"
     tailscale_tag: "{{ lookup('ansible.builtin.env', 'TAILSCALE_TAG', default=undef()) }}"
+    app_domains: "{{ lookup('ansible.builtin.env', 'APP_DOMAINS', default='') }}"
+    canonical_domain: "{{ lookup('ansible.builtin.env', 'CANONICAL_DOMAIN', default='') }}"
```

### 8.5 Coolify: remember domains are registered at creation

`infra/playbooks/deploy_application.yml` only sets fields when it **creates** the
application. To change domains on an existing app, patch it via the Coolify API
or the UI. The per-solution diffs below add the create-time field; an optional
`PATCH` task is included in Section 9.

### 8.6 WAF / IPS and real client IPs

- Enable Traefik access logs (see the operator guide "Step 4") so **CrowdSec**
  (already installed with the Traefik/Caddy collections) can inspect traffic.
- If a CDN/tunnel sits in front, configure `X-Forwarded-For` handling so
  CrowdSec and Fail2Ban see real visitor IPs, not the CDN's.
- Keep the existing Fail2Ban `django-disallowedhost` jail.

### 8.7 Observability

`infra/gatus/config.yml` — add a **public** probe (the existing `app-external`
resolves via Tailscale MagicDNS, so it is not a true public check).

```diff
   - name: app-external
     group: application
     url: https://${TS_APP_DOMAIN}/api/health
     interval: 5m
     client:
       dns-resolver: "tcp://100.100.100.100:53"
     conditions:
       - "[STATUS] == 200"
       - "[CERTIFICATE_EXPIRATION] > 48h"
+
+  - name: app-public
+    group: application
+    url: https://${CANONICAL_DOMAIN}/api/health
+    interval: 5m
+    conditions:
+      - "[STATUS] == 200"
+      - "[CERTIFICATE_EXPIRATION] > 720h"
```

> Add `CANONICAL_DOMAIN` to the `gatus` service environment in
> `docker-compose.coolify.yml` (alongside `TS_APP_DOMAIN`).

---

## 9. Per-solution plans

Each plan lists: **who it suits**, **how it works**, **cost/security**, and the
**diff-level changes**. All plans assume Section 8 is applied first.

### Solution A — Coolify Traefik + Let's Encrypt HTTP-01

**Suits:** the fastest path to a working public domain; specific hostnames only;
origin IP exposure is acceptable.

**How it works:** Coolify's Traefik listens on 80/443, gets a certificate per
domain via the HTTP-01 challenge (serving a file on port 80), and routes by the
`Host` header to the Django container on port 5000.

**Cost/security:** £0. Exposed origin, protected by TLS, CrowdSec and Fail2Ban.
Requires public port 80 and 443.

**Diff-level plan**

`infra/playbooks/deploy_application.yml` — set domains at creation. Coolify
needs the container port (5000) in each domain so it knows where to route.

```diff
           ports_exposes: "5000"
           ports_mappings: "80:5000"
+          # Comma-separated public FQDNs; :5000 is the in-container port.
+          domains: >-
+            {{ app_domains.split(',') | map('regex_replace', '$', ':5000')
+               | map('regex_replace', '^', 'https://') | join(',') }}
           name: "neuromancers_network"
```

`infra/playbooks/tasks/configure_firewall.yml` — allowed ports already contain
80/443; remove the stale public `8080`.

```diff
   loop:
     - "22" # SSH
     - "80" # HTTP
-    - "8080" # HTTP
     - "443" # HTTPS
     - "{{ crowdsec_port }}"
```

**DNS:** create an `A` (and optional `AAAA`) record per domain → Hetzner IP,
**DNS-only** during first issuance.

**Note:** for an existing application, patch domains afterward:

```diff
+# Update domains on an existing Coolify application.
+- name: Update application domains
+  ansible.builtin.uri:
+    url: "{{ coolify_api_url }}/applications/{{ coolify_application_uuid }}"
+    method: PATCH
+    headers:
+      Authorization: "Bearer {{ coolify_api_token }}"
+    body_format: json
+    body:
+      domains: >-
+        {{ app_domains.split(',') | map('regex_replace', '$', ':5000')
+           | map('regex_replace', '^', 'https://') | join(',') }}
+    status_code: 200
```

---

### Solution B — Coolify Traefik + Let's Encrypt DNS-01 (recommended baseline)

**Suits:** wildcards, port 80 closed, or a CDN/tunnel in front; provider-neutral
automation.

**How it works:** identical to A, but certificate ownership is proven by writing
a temporary `_acme-challenge` TXT record via the DNS provider's API (Lego). No
public port 80 is required, and wildcards become possible.

**Cost/security:** £0. Same exposure as A (unless combined with E/F). Requires a
**zone-scoped DNS API token** in Bitwarden (e.g. `IONOS_API_KEY`,
`CF_DNS_API_TOKEN`).

**Diff-level plan**

1. Apply the same `deploy_application.yml` and firewall diffs as **A**.
2. Configure DNS-01 on the Coolify proxy once (Server → Proxy, or
   `/data/coolify/proxy/docker-compose.yml`). This is **not** currently managed
   by Ansible; either template it (recommended, avoids drift) or document it as a
   manual step. Example for IONOS (swap provider/keys for Cloudflare, Hetzner,
   etc.):

```diff
         command:
           - '--certificatesresolvers.letsencrypt.acme.httpchallenge=true'
           - '--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=http'
+          - '--certificatesresolvers.letsencrypt.acme.dnschallenge=true'
+          - '--certificatesresolvers.letsencrypt.acme.dnschallenge.provider=ionos'
+          - '--certificatesresolvers.letsencrypt.acme.dnschallenge.delaybeforecheck=10'
           - '--certificatesresolvers.letsencrypt.acme.storage=/traefik/acme.json'
         environment:
+          - IONOS_API_KEY=${IONOS_API_KEY}
```

**DNS:** an `A` record per hostname, or a wildcard `A`/CNAME plus a wildcard
certificate request (`*.neuromancers.org.uk`).

**Wildcards:** a domain entry of `https://*.neuromancers.org.uk:5000` plus
DNS-01 produces a wildcard certificate. Coolify cannot issue certs for a pure
catch-all, so enumerate the wildcard explicitly.

---

### Solution C — Coolify Caddy + Let's Encrypt

**Suits:** teams who prefer the Caddyfile model or need a Caddy-specific feature.

**How it works:** Coolify's proxy is switched from Traefik to Caddy. Caddy
manages certificates and routing; DNS-01 requires a Caddy binary **compiled with
the DNS provider module** (Coolify provides an inline-build example).

**Cost/security:** £0. Same exposure model as A/B.

**Diff-level plan**

- No changes to this repository's compose file beyond Section 8.
- One-time server change: switch the Coolify proxy to Caddy and, for DNS-01,
  replace the image with an inline-built one:

```diff
       caddy:
         container_name: coolify-proxy
-        image: 'lucaslorentz/caddy-docker-proxy:2.8-alpine'
+        build:
+          dockerfile_inline: |
+            FROM caddy:2.11-builder AS builder
+            RUN xcaddy build \
+              --with github.com/lucaslorentz/caddy-docker-proxy/v2@v2.8.11 \
+              --with github.com/caddy-dns/ionos/v2@v2.0.0
+            FROM caddy:2.11-alpine
+            COPY --from=builder /usr/bin/caddy /usr/bin/caddy
+            CMD ["caddy", "docker-proxy"]
         environment:
           - CADDY_DOCKER_POLLING_INTERVAL=5s
+          - IONOS_API_KEY=${IONOS_API_KEY}
         labels:
           - coolify.managed=true
           - coolify.proxy=true
+          - caddy.acme_dns=ionos {env.IONOS_API_KEY}
```

> The Coolify team recommends Traefik over Caddy; choose C only if you are
> comfortable maintaining it.

---

### Solution D — Self-managed edge (Caddy/Traefik) declared in the repo

**Suits:** maximum portability and "everything in git"; willingness to run your
own edge.

**How it works:** add a Caddy (or Traefik) service to
`docker-compose.coolify.yml` on ports 80/443, and stop Coolify's built-in proxy
from claiming those ports (point it at different ports or disable it). Caddy
routes by hostname to `django:5000` and gets certificates automatically.

**Cost/security:** £0. Same exposure model as A/B. Trade-off: more surface to
operate and a conflict to resolve with Coolify's proxy.

**Diff-level plan**

`docker-compose.coolify.yml` — add Caddy sharing the stack network:

```diff
 services:
+  caddy:
+    image: caddy:2.9
+    restart: unless-stopped
+    ports:
+      - "80:80"
+      - "443:443"
+    environment:
+      - APP_DOMAINS=${APP_DOMAINS}
+      - CANONICAL_DOMAIN=${CANONICAL_DOMAIN}
+    volumes:
+      - caddy-data:/data
+      - caddy-config:/config
+      - /opt/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
+    depends_on:
+      django:
+        condition: service_healthy
+
 volumes:
   postgres-data:
   postgres-backups:
   redis-data:
   gatus-data:
+  caddy-data:
+  caddy-config:
```

`/opt/caddy/Caddyfile` (deployed by Ansible from a repo template):

```
{$CANONICAL_DOMAIN} {
    encode zstd gzip
    reverse_proxy django:5000
}

# Aliases that redirect to the canonical host:
network.example.com {
    redir https://{$CANONICAL_DOMAIN}{uri} permanent
}
```

> **Conflict:** Coolify's proxy also binds 80/443. Resolve by changing Coolify's
> proxy ports (Server → Proxy) or disabling it. Document the choice; two proxies
> cannot share the same ports.
> **Caveat:** do **not** add custom `networks:` sections to the compose file
> (Coolify intermittently fails to route across them).

---

### Solution E — Cloudflare Tunnel (recommended hardening)

**Suits:** origin IP must not appear on the public internet; no inbound ports.

**How it works:** a `cloudflared` container dials **out** to Cloudflare and
maintains an encrypted tunnel. Cloudflare's edge terminates TLS and forwards
traffic through the tunnel to Coolify's proxy on the server. No port 80/443 has
to be open to the world.

**Cost/security:** £0 on Cloudflare's free tier (WAF/DDoS included; optional
Zero Trust Access for SSO). Strongest origin privacy. Trade-off: Cloudflare is in
the request path, and DNS for the tunnelled names lives at Cloudflare.

**Diff-level plan**

`docker-compose.coolify.yml` — add the tunnel service:

```diff
 services:
   tsdproxy:
     image: almeidapaulopt/tsdproxy:dev
@@
   gatus:
     image: ghcr.io/twin/gatus:stable
@@
     depends_on:
       django:
         condition: service_healthy
+
+  cloudflared:
+    image: cloudflare/cloudflared:latest
+    restart: unless-stopped
+    command: tunnel --no-autoupdate run
+    environment:
+      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
+    depends_on:
+      django:
+        condition: service_healthy
```

`infra/playbooks/deploy_application.yml` — push the tunnel token as a Coolify env
var (same mechanism as `TS_APP_DOMAIN`):

```diff
           - key: "TS_PAAS_DOMAIN"
             value: "{{ tailscale_paas_domain }}"
             is_preview: false
             is_literal: true
+          - key: "CLOUDFLARE_TUNNEL_TOKEN"
+            value: "{{ cloudflare_tunnel_token }}"
+            is_preview: false
+            is_literal: true
```

`infra/inventory/hosts.yml` — surface the token:

```diff
+    cloudflare_tunnel_token: "{{ lookup('ansible.builtin.env', 'CLOUDFLARE_TUNNEL_TOKEN', default=undef()) }}"
```

`infra/playbooks/tasks/configure_firewall.yml` — with a tunnel, the public
internet no longer needs 80/443:

```diff
 - name: Allow public application ports only
   community.general.ufw:
     rule: allow
     port: "{{ item }}"
     proto: tcp
   loop:
     - "22" # SSH
-    - "80" # HTTP
-    - "443" # HTTPS
     - "{{ crowdsec_port }}"
```

**Cloudflare dashboard:** create a tunnel, add a public hostname per domain with
service `http://coolify-proxy:80` (or `http://localhost:80` if cloudflared runs
on the host), and let Cloudflare create the CNAME records. Optionally add
**Cloudflare Access** policies for `/admin` or `/flower`.

**Certificates:** Cloudflare's edge certificate covers visitors; the origin
leg is inside the tunnel. Set the origin SSL mode appropriately
(Full/Full-Strict with an Origin certificate if you also terminate TLS at
Coolify).

> Follow Cloudify's official Cloudflare Tunnel guide for the exact dashboard
> steps; the compose/firewall changes above are what this repository needs.

---

### Solution F — Cloudflare proxied DNS + Origin/LE certificate

**Suits:** hide the origin IP while keeping a conventional (non-tunnel) setup.

**How it works:** DNS records are proxied ("orange cloud") through Cloudflare.
Visitors get a Cloudflare edge certificate; Cloudflare connects to the origin on
443, which presents a Let's Encrypt (DNS-01) or Cloudflare Origin certificate.

**Cost/security:** £0. Origin IP hidden; WAF/DDoS available. Requires port 443
open. Trade-off: Cloudflare in the path.

**Diff-level plan**

1. Apply Section 8 (Django), and the DNS-01 pieces from **B** so certificates
   can be issued while records are proxied.
2. Restrict the origin firewall to Cloudflare's published IP ranges so direct
   origin access is blocked:

```diff
+# Only Cloudflare may reach the origin web ports.
+- name: Allow Cloudflare edge IPs to 80/443
+  community.general.ufw:
+    rule: allow
+    from_ip: "{{ item }}"
+    port: "{{ port }}"
+    proto: tcp
+  loop: "{{ cloudflare_ipv4_ranges }}"
+  loop_control:
+    loop_var: item
```

3. In Cloudflare, set each record to **Proxied**, SSL/TLS mode **Full (Strict)**,
   and enable "Authenticated Origin Pulls" where supported.

---

### Solution G — Tailscale Funnel (not recommended for this requirement)

**Suits:** a handful of users, `*.ts.net` URLs acceptable.

**Why not:** Funnel serves **only** `*.ts.net` names, is in beta, is
bandwidth-limited, and restricts ports to 443/8443/10000. A custom domain cannot
get a valid certificate directly (the certificate is for the `*.ts.net` name), so
a front proxy is still required — which defeats the purpose. **Keep the current
private tsdproxy setup for tailnet access; do not use Funnel for the public
multi-domain endpoint.**

**Diff-level plan:** none recommended. If ever required, it is enabled with
`tailscale funnel` and a `funnel` node attribute in the tailnet policy file.

---

### Solution H — External load balancer / second VPS (not recommended)

**Suits:** large scale or a hard requirement to isolate the origin behind a
managed device.

**Why not:** adds cost (~€5.5+/mo for a Hetzner Load Balancer, more for a second
VPS) and operational complexity, with no security benefit over **E** for our
scale. Rejected on cost-efficiency.

**Diff-level plan:** none.

---

## 10. Middlewares (shared by A/B/C/E/F)

Security headers, rate limiting and alias redirects are configured once and
referenced from the `django` service using Coolify's shorthand label (works with
the docker-compose build pack):

```diff
   django:
     image: ghcr.io/baldwinboy/neuromancers-network:${DOCKER_TAG:-latest}
+    labels:
+      - "traefik.http.middlewares.sec-headers.headers.stsSeconds=31536000"
+      - "traefik.http.middlewares.sec-headers.headers.contentTypeNosniff=true"
+      - "traefik.http.middlewares.sec-headers.headers.browserXssFilter=true"
+      - "traefik.http.middlewares.sec-headers.headers.frameDeny=true"
+      - "traefik.http.middlewares.rate.ratelimit.average=100"
+      - "traefik.http.middlewares.rate.ratelimit.period=1m"
+      - "coolify.traefik.middlewares=sec-headers,rate"
     environment:
       - BWS_ACCESS_TOKEN=${BWS_ACCESS_TOKEN}
       - TS_APP_DOMAIN=${TS_APP_DOMAIN}
```

Alias redirects (secondary domain → canonical) can be defined in Traefik's
dynamic configuration (Server → Proxy → Dynamic Configurations) or as an
additional router with a `redirectregex` middleware.

---

## 11. Risks and current-state findings

| Finding | Impact | Action |
|---------|--------|--------|
| `CSRF_TRUSTED_ORIGINS` missing in production settings | Form POSTs/logins fail on the custom domain | Add (Section 8.2) |
| `CUSTOM_DNS` defaults to `1.1.1.1` | Placeholder pollutes `ALLOWED_HOSTS` | Replace with `APP_DOMAINS` (Section 8.2) |
| Wagtail matches `Site.hostname` | Aliases may 404 or redirect unexpectedly | Create Sites or a canonical middleware |
| `ports_mappings: "80:5000"` in `deploy_application.yml` | May publish Django directly, bypassing proxy/TLS | Verify under the compose build pack; remove if exposed |
| Public `8080` allowed in UFW | Unused, wider attack surface | Remove (Section 9/A) |
| Legacy `docker-compose.production.yml` + single-host Traefik | Unused, confusing duplicate ingress | Consider deleting |
| Coolify DNS-01 proxy config is not Ansible-managed | Configuration drift | Template it or document as manual |
| `network.neuromancers.org.uk` currently returns HTTP 521 | Public name points at a dead origin | Fix DNS/routing as part of rollout |
| Let's Encrypt rate limits | Many domains can hit limits during testing | Test against the LE staging endpoint first |

---

## 12. Verification checklist

After implementing the chosen solution:

- [ ] `https://<each-domain>/api/health` returns `200` with a valid certificate.
- [ ] Browser padlock shows the correct hostname; `Strict-Transport-Security` present.
- [ ] Secondary/vainty domains behave as chosen (serve or 301 to canonical).
- [ ] Certificate auto-renewal path verified (LE staging test, then production).
- [ ] Coolify dashboard, tsdproxy and Gatus are **not** reachable publicly.
- [ ] CrowdSec and Fail2Ban log real client IPs (not the CDN/tunnel IP).
- [ ] Gatus `app-public` probe is green and tracks certificate expiry.
- [ ] `APP_DOMAINS`/`CANONICAL_DOMAIN` are in Bitwarden; no secrets in git.

---

## 13. Open items to confirm before implementation

1. **Registrar / DNS provider** and whether a zone-scoped API token can be
   issued (decides HTTP-01 vs DNS-01 and wildcard feasibility).
2. **Canonical domain** and which aliases redirect vs serve.
3. **Final ingress:** Coolify Traefik (+ optional Cloudflare proxy) or Cloudflare
   Tunnel (if "no open ports" is worth the Cloudflare coupling).
4. **Ansible-manage Coolify's DNS-01 proxy config** (avoids drift) or document
   it as a manual one-time step.

---

## Appendix — variable reference

| Variable | Where | Purpose |
|----------|-------|---------|
| `APP_DOMAINS` | Bitwarden → Ansible → Coolify | Comma-separated public FQDNs, canonical first |
| `CANONICAL_DOMAIN` | Bitwarden → Ansible → Coolify/Gatus | Preferred name for redirects and Wagtail |
| `CSRF_TRUSTED_ORIGINS` | Coolify env (optional) | Extra trusted origins beyond `APP_DOMAINS` |
| `IONOS_API_KEY` / `CF_DNS_API_TOKEN` / … | Bitwarden → Coolify proxy | DNS-01 provider credential (zone-scoped) |
| `CLOUDFLARE_TUNNEL_TOKEN` | Bitwarden → Coolify | Cloudflare Tunnel credential (Solution E) |
| `TS_APP_DOMAIN` | existing | Private tailnet address (unchanged) |
| `TS_PAAS_DOMAIN` | existing | Private Coolify address (unchanged) |
