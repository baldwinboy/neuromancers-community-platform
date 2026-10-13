# NEUROMANCERS Network — Roadmap (remaining work)

> Status: **Phases 1–7 are implemented and committed.** The user-safety and
> moderation program (see §1) is implemented and committed. The Operations
> admin now uses hidden `SnippetViewSet`s for bulk-capable viewsets, and member
> notification opt-outs are edited with checkbox lists.
>
> This document lists **only what remains**. Completed work is not restated.

## Cross-cutting principles (unchanged)

- App code owns models, selectors, services, actions, form-field types and
  daisIE registries. **All UI is authored in the Wagtail admin.**
- **Reuse, don't re-implement**: `search_*`, `create_booking`,
  `sync_meeting_durations`, daisIE context models/filters/actions, the
  Stripe/dj-stripe plumbing, the inbox event bus, and the daisIE form pages.
- **Additive schema only**; one committed migration per change;
  `makemigrations --check` must stay clean.
- Signal-driven writes are failure-isolated; **tests affirm pure behaviour**,
  not event/audit wiring.

## Verification (run after each change)

```sh
just manage makemigrations --check --noinput
just manage check
just pytest
```

---

# 1. Access guard and pairwise block filtering (WS-G) — *pinned*

The blanket "a deactivated member's objects are not reachable by others"
guarantee. Deactivation, deletion and blocking currently ship their data and
feeds but not this enforcement layer.

- **Pages (blanket):** a `before_serve_page` hook returning a 404 (daisIE error
  page) when the resolved page's `source` owner is deactivated/blocked and the
  viewer is neither the owner nor a moderator.
- **Selectors/API:** owner-active filters in `meetings.selectors.published_reviews`,
  `core.models.pages.SearchPage`, `peers/api.py`, `meetings/api.py`,
  `peers.selectors.peer_calendar_events`, and bookmark selectors.
- **Middleware:** `DeactivatedAccountMiddleware` to force-log-out an
  authenticated-but-inactive session and guard app-owned object URLs
  (settings forms, meetings htmx, calendar feed).
- **Block filtering:** layer the pairwise `blocked_user_ids` filter (already
  implemented with the blocking model) into the same guard — viewer-scoped
  exclusion in selectors, `create_booking`, and the page hook.

---

# 2. Exposure, seeding, docs (WS8)

- Register any remaining actions / audiences / form-field types.
- **New** `core/management/` package and
  `core/management/commands/seed_account_selfservice.py` (idempotent,
  `--force`): seed the settings pages/forms for deactivate / delete / blocks /
  export / sessions, the moderation/support pages, and the feeds.
- **Schedule the background tasks:** add a `django_celery_beat` data migration
  for `purge_due_account_deletions` and `build_data_export`.
- **Admin Help articles:** deferred from the safety program — seed
  non-technical, seventh-grade, idempotent articles covering deactivation,
  deletion, blocking, bans, reporting/support, data export, session revoke and
  calendar-token controls.

---

# 3. Cleanup

- **Consolidate the TOS reset.** `ResetTosView` (`core/views/tos.py` +
  `ResetTosForm` + admin URL) duplicates `ResetTosBulkAction` on
  `UserProfileViewSet`. Keep a single `ConfirmBulkAction` path.

---

# 4. Remaining roadmap phases (unchanged scope)

## Phase 8 (remainder) — Blog and Contact

- **Blog** — a `StandardPage`-based blog index + post detail (feeds and detail
  pages), admin-authored. No app models unless required.
- **Contact** — a `DaisieFormPage` contact form (topics as a small taxonomy or
  choice list), admin-authored.
- *(Host dashboard selectors and booking/refund actions are already
  implemented.)*

## Phase 9 — Admin Help guide reader

- Keep `HelpArticle` / `HelpCategory` / `GlossaryTerm` as editable snippets.
- Add a staff-only reader: `core/views/help.py` + one template, registered via
  `register_admin_urls`, a help-menu hook and a dashboard panel. Renders
  articles grouped by category (`body`/`steps` StreamFields). No schema change.

## Phase 10 — `seed_help_guide` command

- Idempotent `get_or_create` management command (never clobbers edits).
- Seeds the five categories, the article set, and the glossary — including
  Stripe, Stripe Connect, Express dashboard, Whereby, GetPronto, Daily, and the
  non-technical concepts (Project, Platform, Django, Wagtail, daisIE,
  Environment, Repository, Deployment, IaC, Ansible, GitHub, Coolify, Secrets,
  Hetzner, Tailscale, Cloudflare, DNS, API key, webhook, OAuth, KYC, ICS, tag
  group, allowed tag, taxonomy, etc.).
- Idempotency verified by running the command twice.

## Phase 11 — `seed_pages` command (MVP-style pages)

- Re-runnable `core/management/commands/seed_pages.py`; `--force` overwrites,
  otherwise only fills empty bodies. Runs after `core/0003_seed_chrome`.
- **Signed-in pages** are `core.StandardPage` with an `audience` block
  (`authenticated`): `/settings`, `diary`, `inbox`, `/meetings`, `/dashboard`,
  `/search`.
- **Feed snippets** seeded by name: `meetings-published`, `bookings-upcoming`,
  `unpaid-bookings`, `notifications-user`, optional `reviews-published`.
- **Home chrome** — seed the home `hero` and the Main navigation / Footer
  `DaisyUIMenu` bodies.
- Idempotent `get_or_create` for feeds/menus; `--force` to overwrite page
  bodies. Idempotency verified by running twice.

## Phase 12 — Admin-controlled allauth pages & emails (daisIE 3.2.0)

- Bump `wagtail-daisie[...]` to `==3.2.0` (adds `ReusableBlock` /
  `EmailReusableBlock` + the `reusable` email block); refresh `uv.lock`.
- `UserSignupForm` gains `name`, `date_of_birth`, `accepted_tos` and persists
  them; trim `ACCOUNT_SIGNUP_FIELDS` to native keys.
- One reusable email header + footer, live-referenced by every template.
- Idempotent `ensure_daisie_templates` command (`--force`, `--pages-only`,
  `--emails-only`): 17 allauth pages + 20 allauth emails + 27 notification
  emails; per-category CTA rules; pure builders in `core/daisie_seed.py` for
  unit testing.
- Override `wagtail_daisIE/blocks/inputs/_autocomplete_ui.html` in the project.
- **Definition of done:** checks clean; the command re-run is a no-op; the
  reusable footer edit propagates to every template.

---

# 5. Operations and legal

- **Trusted proxies:** set `RATELIMIT_TRUSTED_PROXIES` (Traefik/Cloudflare
  CIDRs) **before** enabling IP-ban enforcement (`BanSettings.ip_enforcement_enabled`,
  currently shadow-only). Until then, IP bans only record and log.
- **Legal review:** confirm the deletion anonymisation retains the financial
  records the platform must keep (Stripe/tax) — `UNVERIFIED`.
- **Performance:** consider caching `BanSettings` in `BanMiddleware` if the
  per-request load shows up in profiling.
- **Session list UI** (optional): a browsable session list needs decoding every
  DB session; only revoke actions ship today.

## Appendix — housekeeping

```sh
just manage makemigrations --check --noinput
just manage check
just pytest
just manage seed_help_guide && just manage seed_pages && just manage seed_pages
just manage ensure_daisie_templates && just manage ensure_daisie_templates
```

- Migrations are additive and committed per change.
- Refined tests only; no framework-only tests.
