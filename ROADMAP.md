# NEUROMANCERS Network — Roadmap (remaining work)

> Status: Phases 1–7, the user-safety/moderation program, WS-G (access guard + pairwise blocks), and the account/signup hardening are implemented and committed. This section covers remaining seeding, exposure, docs, cleanup, lifecycle, storage (Tigris) and pricing work.

## Cross-cutting principles (unchanged)

- App code owns models, selectors, services, actions, form-field types and registries. **All UI is authored in the Wagtail admin.**
- **Reuse, don't re-implement**: `search_*`, `create_booking`, `sync_meeting_durations`, daisIE context models/filters/actions, the Stripe/dj-stripe plumbing, the inbox event bus, and the daisIE form pages.
- **Additive schema only**; one committed migration per change; `makemigrations --check` stays clean.
- Signal-driven writes are failure-isolated; tests affirm pure behaviour, not event/audit wiring.
- Every phase ends with the verification block, a **review pause**, and one reviewable commit.

## Verification (run after each change)

```sh
just manage makemigrations --check --noinput
just manage check
just pytest
```

Seed commands must additionally be proven idempotent by running them twice.

---

## 0. Locked decisions

| Area | Decision |
|---|---|
| Subscription lifecycle | **Option 1** — bump `stripe`/`dj-stripe` to versions exposing `stripe.Subscription.pause` and the `customer.subscription.paused`/`resumed` events. Expose **both** cancel-at-period-end and immediate cancel. Restart = fresh checkout; resume = `/resume`. |
| Pause semantics | Stripe-recommended defaults: credit unused time from now, bill outstanding usage through now, `invoicing_behavior=pending_invoice_item`; resume with `payment_behavior=resume_on_payment_success`, `billing_cycle_anchor=now`, `proration_behavior=create_prorations`. |
| Export storage | Private **`exports/` prefix in the existing backups bucket** (root `AWS_*`, Tigris); `FileSystemStorage` for dev/test. Never the public media bucket. |
| Export delivery | Emailed **signed, short-lived download link** (no attachments — daisIE emails support HTML alternatives only). |
| Export format | **ZIP of CSVs** (stdlib `zipfile`+`csv`, per-table `.iterator()`, `SpooledTemporaryFile`). |
| Export limits | **One active export per member + 24 h cooldown**; TTL **48 h**; explicit `expires_at` field. |
| Export maintenance | `sweep_data_exports` (retry stale `PENDING`/`PROCESSING`; purge expired) + `purge_due_account_deletions`, both scheduled via `django_celery_beat`. |
| TOS reset | Keep **only** `ResetTosBulkAction`; add `UserProfileFilterSet`; override `get_all_objects_in_listing_query` to honour the listing query; delete Path A. |
| WS8 registration | Register `is_peer_owner`; delete the dead per-app `HANDLERS` dicts; register daisIE 3.3 attachment/autocomplete form-field types. |
| Storage (Tigris) | **Tigris** (S3-compatible, `t3.storage.dev`) for media (public bucket) and backups/exports (private bucket). Scope here is **documentation + private `exports/` wiring only**. |
| Pricing | Scope is **both**: platform pricing configuration (admin) and infrastructure running costs (developer/operator). |
| Help guide | Staff-only reader (admin support reference) documenting **every** audience’s features. Category 1 targets admins, the first users. |
| Phases | A (Help + registration) → B (Pages) → C (Account self-service + subscription) → D (TOS + export + storage/pricing docs). Review pause between each. |

---

## 1. Exposure, seeding, docs (WS8)

### 1.1 Register remaining extension points
- Add `is_peer_owner` (`core/audience.py`) to `WAGTAIL_DAISIE_AUDIENCE_RULES`.
- Remove the dead per-app `HANDLERS` dicts (`users`, `moderation`, `core`, `inbox`, `meetings`, `peers` actions): no consumer; daisIE resolves handlers from settings only.
- Register the daisIE 3.3 attachment and autocomplete form-field types (confirm exact keys from `wagtail_daisIE.forms.registry`).

### 1.2 `seed_help_guide` (Phase 10)
- New `core/help_seed.yaml` (content) + `core/help_seed.py` (loader/validator): load and shape the catalogue; malformed data fails loudly.
- New `core/management/commands/seed_help_guide.py` — idempotent `get_or_create`; **never clobbers admin edits**.
- Seeds the five categories, ~55 articles (including per-audience Feature indexes and the Tigris/pricing articles) and the glossary (catalogue in §6).
- Idempotency proven by running twice.

### 1.3 `seed_pages` (Phase 11 + Phase 8)
- New `core/management/commands/seed_pages.py`; `--force` overwrites bodies, otherwise only fills empty. Runs after `core/0003_seed_chrome`.
- **Signed-in pages** — `StandardPage` + audience block (`authenticated`) for `/settings`, `/diary`, `/inbox`, `/meetings`, `/dashboard`, `/search`; **reconcile** the `/search`, `/dashboard`, `/settings` pages already created by `0003` as dedicated models (do not duplicate).
- **Feed snippets** seeded by name: `meetings-published`, `bookings-upcoming`, `unpaid-bookings`, `notifications-user`, optional `reviews-published`, plus host feeds (`host_meeting`, `host_request`, `host_refund`).
- **Home chrome** — seed the home `hero` and the Main navigation / Footer `DaisyUIMenu` bodies.
- **Phase 8 remainder** — seed a `StandardPage` blog index + post detail, and a `DaisieFormPage` contact form (topics via a small choice list/taxonomy; may need a small page subclass → additive migration, or reuse `moderation.SupportFormPage`).
- Idempotent `get_or_create` for feeds/menus; run twice.

### 1.4 `seed_account_selfservice` (§2)
- New `core/management/` package + `seed_account_selfservice.py` (idempotent; `--force`).
- Seeds the settings/self-service page bodies (Tabs + Action/ActionForm blocks) driving deactivate/reactivate, delete request/cancel, block/unblock, data export, session revoke, calendar token rotate/revoke.
- Seeds the moderation/support pages, the account feeds, and the subscription controls (§2).

### 1.5 Schedule background tasks
- New data migration in the owning app mirroring `meetings/migrations/0003_periodic_tasks.py`.
- Schedules `purge_due_account_deletions` and `sweep_data_exports` via `django_celery_beat`, with a reverse that deletes the `PeriodicTask` rows.

---

## 2. Subscription lifecycle extras (peer plan controls)

- **Dependency:** bump `stripe`/`dj-stripe` for `stripe.Subscription.pause` + `customer.subscription.paused`/`resumed`.
- **Services** (`payments/services.py`):
  - `pause_subscription(profile)` → `/pause` with the Stripe-recommended `bill_for` defaults.
  - `resume_subscription(profile)` → `/resume` (`resume_on_payment_success`, `billing_cycle_anchor=now`, `create_prorations`).
  - `cancel_subscription(profile, *, at_period_end)` → `sub.cancel(at_period_end=…)` (both modes).
- **Actions** (`peers/actions.py`): `peer.subscription_pause|resume|cancel` + labels + `WAGTAIL_DAISIE_ACTIONS`; dashboard buttons.
- **Webhooks** (`peers/signals.py`): handle `paused`/`resumed` — keep the `PeerSubscription` row, call `enforce_subscription_lapse` on pause, emit new events.
- **Events:** add `subscription_paused`, `subscription_resumed` to the event keys + bridges.
- **Eligibility:** unchanged (`paused` already excluded).
- **Tests:** services (mocked Stripe), actions, webhook transitions, eligibility.

---

## 3. Data export redesign (on Tigris)

- **Storage:** `STORAGES["exports"]` on the private Tigris backups bucket/creds under an `exports/` prefix (`FileSystemStorage` for dev/test); `DataExportRequest.file` uses it; add `expires_at` (additive migration).
- **Builder:** `build_export_file` → **ZIP of CSVs** over `.iterator()`; set `completed_at`/`expires_at`; emit `data_export_ready` with `download_url`.
- **Download:** signed, owner/staff-only view streaming `FileResponse(export.file.open("rb"))`.
- **Limits:** reject if a `PENDING`/`PROCESSING` export exists or a `READY` export completed within 24 h; rate-limited.
- **Maintenance:** `sweep_data_exports` retries stale jobs and purges past `expires_at` (48 h).
- **Tests:** ZIP contents, signed-url auth, cooldown, expiry/sweep.

---

## 4. Cleanup — consolidate the TOS reset

- Keep only `ResetTosBulkAction`; add `UserProfileFilterSet` (≥ `accepted_tos`, optionally `visibility`/group); override `get_all_objects_in_listing_query` so filter + select-all reproduces audience-wide reset.
- Delete Path A: `core/views/tos.py`, `ResetTosForm`, `AudienceSelectMultiple`, `audience_choices`, `users_for_audiences`, `ResetTosViewSet` + admin URL + `wagtailadmin/tos/reset.html`, orphan `__pycache__/test_tos_reset*.pyc`.
- Keep the `needs_tos_acceptance` audience rule and queryset.

---

## 5. Admin Help guide reader (Phase 9)

- New `core/views/help.py` + `core/templates/core/help_guide.html` (staff-only).
- Renders articles grouped by category; renders `body` (`ContentBlock`) and `steps` (`HelpStepsBlock`); glossary section.
- Register via `register_admin_urls` (`/cms/help/`), implement `register_help_menu_item`, add a dashboard panel. **No schema change.**

---

## 6. Help content catalogue

Admin-facing support reference (reader is staff-only); each article’s `audience` records **who the article is about**.

**Five categories:** 1 Administrators — Getting started `[admin]` · 2 Administrators — Moderation & operations `[admin]` · 3 Care providers `[peer]` · 4 Care seekers `[seeker]` · 5 Developers & operators `[developer]`.

### 6.0 Setup surfaces these map to
Settings models: `StripeSettings`, `EmailSettings`, `IntegrationSettings`, `LocalizationSettings`, `ModerationSettings`, `NotificationSettings`, `AccountSettings` (`core/models/settings.py`), `PeerRequirementsSettings`, `BanSettings`. Snippets: `DaisyUITheme`, `DaisyUIMenu`, `ReusableBlock`, `ErrorPage`, `DaisyUIIconSource`, `DaisyUIFavicon`, `Feed`, `EmailTemplate`, `EmailReusableBlock`, `Audience`, `EmailCampaign`, `AllauthPageOverride`, `AllauthEmailOverride`, `Language`, `Country`, `TagGroup`, `AllowedTag`. Storage: Tigris (env-driven).

### Category 1 — Administrators: Getting started `[admin]`
| Article | Kind | Summary |
|---|---|---|
| Your admin role and the Operations menu | reference | Reaching the Wagtail admin; what each Operations menu group does. |
| Setting up your site and domain | howto | Configure the Wagtail `Site`, root/home page and reserved routes. |
| Choosing and building a theme | howto | `DaisyUITheme`: colours, radii, sizes, effects, background, fonts; default/light/dark. |
| Building navigation and the footer | howto | `DaisyUIMenu` (Main navigation / Footer): items, branding, search, theme. |
| Designing the homepage | howto | The home `hero` and page content blocks. |
| Configuring email delivery (SMTP) | howto | `EmailSettings` host/port/credentials/TLS and sending a test email. |
| Configuring Stripe and payouts | howto | `StripeSettings`: keys, webhook secret, Connect, charge type, application fee, tax; the webhook endpoint. |
| Configuring platform pricing and fees | howto | Plan price IDs (`PeerRequirementsSettings`), application fee, meeting pricing, tax mode, display currency. |
| Configuring meeting providers | howto | `IntegrationSettings`: Whereby/Daily, room prefix, GetPronto API key. |
| Setting care-provider requirements | howto | `PeerRequirementsSettings`: subscription/KYC/verification gates and plan price IDs. |
| Managing taxonomies | howto | Languages, countries, tag groups and allowed tags. |
| Localization and display currency | howto | `LocalizationSettings`: languages, switcher behaviour, currency/exchange-rate source. |
| Account, moderation and ban settings | howto | `AccountSettings` cooldowns/grace, `ModerationSettings` blocklist, `BanSettings` email/IP. |
| Notification defaults and event types | howto | `NotificationSettings`, bridges, audiences and campaigns. |
| Designing error pages | howto | `ErrorPage` snippets for 400/401/403/404/429/500. |
| Designing account (sign-in) pages and emails | howto | `AllauthPageOverride` / `AllauthEmailOverride`. |
| Building feeds and reusable blocks | howto | `Feed` snippets, `ReusableBlock`, email reusable content. |
| Publishing Terms and Help content | howto | The TOS page/audience and the help categories, articles and glossary. |
| Feature index for administrators (setup) | reference | Every admin setup feature and where to find it. |

### Category 2 — Administrators: Moderation & operations `[admin]`
| Article | Kind | Summary |
|---|---|---|
| Reviewing peer applications | howto | Approving/rejecting applications and the resulting profile state. |
| Managing members and profiles | howto | Editing member profiles and visibility; member operations. |
| Handling support and report tickets | howto | Working the support queue, assignment and resolution. |
| Username moderation and bans | howto | The username blocklist and applying email/IP bans. |
| Resetting Terms acceptance | howto | The single bulk-action path and audience-wide reset. |
| Data exports and deletion requests | howto | Fulfilling exports and processing/undoing deletions. |
| Overseeing bookings, refunds and meetings | howto | Inspecting and acting on bookings, refunds and meetings. |
| Visibility and enforcement rules | reference | How deactivated/blocked/paused-plan and unpublished content is hidden. |
| Feature index for operations | reference | Every moderation/operations feature and where to find it. |

### Category 3 — Care providers `[peer]`
| Article | Kind | Summary |
|---|---|---|
| Becoming a care provider | howto | Applying, moderation approval and the provider agreement. |
| Connecting Stripe (Express + KYC) | howto | Connect onboarding and identity (KYC) verification. |
| Your plan: start, pause, end, restart | howto | Subscription lifecycle controls and their effect on eligibility/visibility. |
| Creating and publishing a meeting | howto | 1:1 vs group meetings, terms, scheduling and recurrence. |
| Pricing your meetings | reference | Fixed, sliding-scale and duration-tier pricing, and currency. |
| Managing meetings | howto | Unpublish, archive, delete, and the unpublish/delete-all controls. |
| Setting your availability | howto | One-off and recurring availability windows and 1:1 slot booking. |
| Host dashboard | howto | Booking requests, approve/reject, refunds and the host feeds. |
| Express dashboard & disconnecting Stripe | howto | Opening the Express dashboard and the effect of disconnecting. |
| Feature index for care providers | reference | Every provider feature and where to find it. |

### Category 4 — Care seekers `[seeker]`
| Article | Kind | Summary |
|---|---|---|
| Creating your account | howto | Username, email, name, date of birth and Terms acceptance; verification. |
| Finding a care provider | howto | The search page, filters and how hidden/blocked content is excluded. |
| Booking a session | howto | Requesting a meeting, approval policies, duration/price and terms. |
| Paying for a booking | howto | Stripe checkout, the unpaid-bookings cart and payment history. |
| Managing your bookings & sessions | howto | Upcoming/paid bookings, cancelling and joining group meetings. |
| Requesting a refund | howto | Refund policy and approval-required refunds. |
| Leaving a review | howto | Reviewing a completed session and where reviews appear. |
| Your inbox & notifications | howto | How inbox events arrive, marking read and opt-outs. |
| Your diary & calendar feed | howto | The diary page and the read-only ICS feed, including token rotation. |
| Feature index for care seekers | reference | Every member feature and where to find it. |

### Category 5 — Developers & operators `[developer]`
| Article | Kind | Summary |
|---|---|---|
| Object storage with Tigris | reference | Media/public bucket, private backups + exports, env vars, custom domain, S3 compatibility. |
| Storage, backups and data retention (overview) | reference | What is stored where (Tigris media vs private backups/exports) and the retention windows. |
| Infrastructure and running costs | reference | Hetzner host; Tigris storage/egress (zero egress; $0.02/GB Standard; free 5 GB; Class A/B request rates); Stripe fees; DNS/Coolify/Tailscale; what drives the bill. |
| Stripe, Connect and Express explained | reference | Payments, payouts and the platform/connected-account model. |
| Video providers: Whereby, GetPronto, Daily | reference | Meeting-room providers and how links are generated. |
| The platform stack | reference | Django, Wagtail, daisIE, Environment, Repository, Deployment, IaC, Ansible, GitHub, Coolify, Secrets, Hetzner, Tailscale, Cloudflare, DNS. |
| Webhooks, API keys, OAuth, KYC | reference | The integration concepts underpinning payments and identity. |
| Taxonomy: tag groups, allowed tags, languages, countries | reference | How filters and tagging are structured. |
| Glossary | reference | The glossary terms below. |

### Glossary terms (seeded `GlossaryTerm`)
Stripe · Stripe Connect · Express dashboard · payment profile · subscription · plan pause/resume/cancel · application fee · peer plan price · Whereby · GetPronto · Daily · Tigris · object storage bucket · egress · retention · Project · Platform · Django · Wagtail · daisIE · Environment · Repository · Deployment · IaC · Ansible · GitHub · Coolify · Secrets · Hetzner · Tailscale · Cloudflare · DNS · API key · webhook · OAuth · KYC · ICS · tag group · allowed tag · taxonomy · feed · audience · reserved route · deactivation · deletion/anonymisation · blocking · ban · data export · session · calendar token · provider agreement.

*(Each term gets a one–two sentence, seventh-grade definition in the seed data.)*

---

## 7. Storage & infrastructure (Tigris) — tasks

Scope: **documentation + private `exports/` wiring only** (no new integration).

- **Document the storage architecture** in `docs/infra/` and the help guide: public media bucket (`DJANGO_AWS_*`, `AWS_S3_CUSTOM_DOMAIN=t3.storage.dev`) vs private backups bucket (root `AWS_*`); the private `exports/` prefix; `RETENTION_DAYS` (30) for backups; 48 h for exports.
- **Ensure no PII in the public media bucket.** Audit what lands in `media` (avatars, documents) and confirm exports never do.
- **Wiring:** add the `exports` alias (§3) using the private backups creds; document the env mapping (`docs/infra/coolify-env-mapping.md`, `docs/infra/secrets-runbook.md`).
- **Retention review:** confirm backup and export retention windows are documented; no lifecycle-rule automation in scope.

## 8. Pricing & fees — tasks

Scope: **both** platform pricing configuration and infrastructure cost.

- **Document and verify platform pricing configuration:** peer plan price IDs (`PeerRequirementsSettings.peer_plan_price_ids`), application fee (`StripeSettings.application_fee`), meeting pricing types (fixed/sliding/duration tiers), tax mode, display currency/exchange (`LocalizationSettings`).
- **Seed the admin pricing article** (§6 Category 1) and the developer cost article (§6 Category 5).
- **Single cost picture** for operators: Tigris + Hetzner + Stripe (§7–8).
- No code change expected unless a pricing setting is found unwired (`UNVERIFIED` until audited).

## 9. Phases, verification and review gates

- **Phase A — Help + registration.** Reader (§5), `seed_help_guide` (§1.2, catalogue §6 incl. Tigris/pricing), extension-point registration (§1.1). Verify: seed twice (no-op); reader renders; gates clean.
- **Phase B — Pages.** `seed_pages` (§1.3) incl. Blog/Contact. Verify: seed twice; gates clean.
- **Phase C — Account self-service + subscription.** `seed_account_selfservice` (§1.4), subscription lifecycle (§2), beat migration (§1.5). Verify: tests; seed twice; gates clean.
- **Phase D — TOS + export + storage/pricing docs.** TOS consolidation (§4), export redesign (§3), Tigris/pricing docs (§7–8), sweep scheduling. Verify: tests; gates clean.

Each phase: small reviewable diffs → verification block → `just pytest` handover → **pause for review**.
