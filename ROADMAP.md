# NEUROMANCERS Network — Roadmap (Phases 7–11)

> Status: **Phases 1–6 are implemented and committed** (filters, availability
> enforcement, admin-authored Settings page, peer-session support + host edit
> page + duration-tier repeater, privacy-aware calendar, notification inbox).
>
> This document is the finalised plan for **Phase 7 through Phase 11**. It
> supersedes all earlier drafts. Every phase is designed for **production-grade
> code with no regressions**, prioritising **legal compliance, accessibility,
> maintainability and cost**; where Stripe provides a cost-efficient solution
> that matches the need, that solution is used.

## Cross-cutting principles

- App code owns models, selectors, services, actions, form-field types and
  daisIE registries. **All UI is authored in the Wagtail admin** (blocks,
  feeds, tabs, actions, pages). Nothing is hard-coded unless it is objectively
  required (e.g. an upload handler or an audience predicate).
- **Reuse, don't re-implement**: `search_*`, `create_booking`,
  `sync_meeting_durations`, daisIE context models/filters/actions, and the
  existing Stripe/dj-stripe plumbing.
- **Additive schema only**; one committed migration per change;
  `makemigrations --check` must stay clean.
- **HTMX** is reused (django-htmx + `WAGTAIL_DAISIE_HTMX`); new endpoints are
  minimal GET fragments only.
- **Signal-driven writes are failure-isolated** so a sync error can never break
  the caller's transaction.
- Tests are **refined, not duplicated**; framework-only tests are pruned.

## Verification (run after each phase)

```sh
just manage makemigrations --check --noinput
just manage check
just pytest
```

---

# Phase 7 — Payments parity, cart, avatar, disconnect

**Goal:** direct-charge Stripe Connect (peer is merchant of record, UK),
admin-controlled fees and tax, compliance gates, multi-peer cart, refunds,
payment history/receipts, provider agreement, ToS re-acceptance, avatar upload,
and connected-account webhooks.

## Decisions (locked)

| Topic | Decision |
|---|---|
| Charge model | **Direct charges** — peer's connected account is merchant of record; peer bears Stripe processing |
| Jurisdiction | United Kingdom |
| Platform fee | Admin-set % taken **out of** the peer's payment; **meetings only** |
| Subscriptions | Billed by the platform via the **Stripe Dashboard**; hard gate |
| KYC gate | `kyc_completed` (≈ `charges_enabled` + `payouts_enabled` + no due requirements) |
| Refunds | Auto/review per meeting; partial refunds behind an admin toggle; allowed anytime post-payment; Stripe processing fee non-refundable |
| Cart | Multi-peer; **one Checkout Session per peer** via a “Pay all” button |
| ToS | Signup checkbox **plus** `needs_tos_acceptance` audience + `accept_tos` action + admin reset (bulk + dedicated view) |
| Templates | Multiple named **terms** and **access-needs** templates |
| Receipts | Link to Stripe’s **hosted receipt** |
| Tax | Stripe Tax **on by default**, admin opt-out |
| Account type | **Express** (includes the Express dashboard) |
| Currency | Per-peer currency; cross-currency via Stripe adaptive pricing |

## A. Stripe settings (admin)

`core/models/settings.py::StripeSettings` gains:

- `charge_type` — `direct` (default) / `destination` / `separate` (fallback).
- `connect_country` — default `GB`.
- `allow_partial_refunds` — boolean.
- `tax_mode` — `stripe_tax` (default) / `off`.
- `subscription_enabled` — boolean (shows the “subscribe” button).

Keep `application_fee` (%). Add panels. Migration **`core/0006`**.

## B. Direct charges, tax and receipts

- `Booking.create_checkout_session` / `MeetingRequest.create_checkout_session`
  create the Checkout Session **on the connected account**
  (`stripe_account=<acct>`) with `application_fee_amount` = admin % and
  `automatic_tax={"enabled": True}` when `tax_mode = stripe_tax`.
- Store/derive the **hosted receipt URL** from the payment intent’s charge so
  the payment-history page can link to it.
- Keep the existing destination-charge code path behind `charge_type =
  destination` (no regression if the admin switches).

## C. Eligibility gating

- “Bookable/publishable” requires `kyc_completed`.
- `create_booking` and checkout refuse ineligible peers with a clear message.
- Feed selectors exclude meetings whose peer is currently ineligible.

## D. Subscription gate and lapse

On any `PeerSubscription` change:

- **1:1 meetings** → `unpublish`.
- **Group meetings with no paid bookings** → `unpublish`.
- **Group meetings with paid participants** → stay published but **hidden from
  feeds** and **block new bookings** (existing paid participants retain access).

Expose an admin-enabled **`peer.subscribe`** button (plan price IDs from
`PeerRequirementsSettings.peer_plan_price_ids`).

## E. Refunds

- Partial refunds when `allow_partial_refunds` (amount input).
- Issued against the **connected account**; allowed anytime after payment.
- Auto vs review unchanged (`Meeting.refund_requires_approval`).
- UI copy states the Stripe processing fee is non-refundable.

## F. Terms, provider agreement, meeting terms, templates

**Signup ToS**
- `users/forms.py::UserSignupForm` gains a required `accept_tos` checkbox
  (linked to the T&Cs `StandardPage`); on signup it sets
  `User.accepted_tos = True`. No schema change.

**Re-acceptance**
- New audience rule **`needs_tos_acceptance`** (`core/audience.py` +
  `WAGTAIL_DAISIE_AUDIENCE_RULES`) with a predicate
  (`authenticated ∧ ¬accepted_tos`) **and** an optional `queryset`.
- Add `queryset`s to `authenticated`, `peer`, `verified_peer`, `moderator` so
  the admin view can target audiences.
- New action **`accept_tos`** (sets `request.user.accepted_tos = True`;
  idempotent; auth-only) in `WAGTAIL_DAISIE_ACTIONS`.
- Admins build an alert/page with `audience = needs_tos_acceptance` and an
  `accept_tos` button.
- **Reset controls:** (a) `ResetTosBulkAction` on `UserProfileViewSet`
  (Operations → Profiles); (b) a dedicated admin view (registered via
  `register_admin_urls`, surfaced under Operations) with an audience dropdown
  (rules that define a `queryset`) + “All users”, with confirmation.

**Provider agreement**
- `PeerProfile` gains `provider_agreement_accepted_at` and
  `provider_agreement_version`.
- Action `peer.accept_provider_agreement`; enforced before Connect
  onboarding/dashboard and before publishing. Content is an admin-authored
  `StandardPage`; acceptance is an admin-authored `ActionFormBlock`.

**Meeting terms**
- Publishing requires **non-empty terms** (validation).
- Multiple named **terms templates** on `PeerProfile.terms_templates` and
  **access-needs templates** on `UserProfile.access_needs_templates` (JSON lists
  of `{name, body}`).
- Actions `meetings.apply_terms_template`; an access-needs template picker on
  booking. Keep `meetings.restore_default_terms`.

## G. Payment history and receipts

- **Peers:** the Stripe **Express dashboard** (payouts, fees, refunds, disputes,
  tax documents).
- **Seekers:** an admin-authored **payment-history feed** (context model over
  bookings/payment intents) showing status, amount and a **hosted receipt
  link**.

## H. Cart (per-peer “Pay all”)

- `unpaid_booking` context model + a daisIE-authored feed/filters.
- Action `bookings.checkout_many`: groups the selected bookings by peer and
  starts **one Checkout Session per peer** (sequential).

## I. Disconnect

- Action `peer.stripe_disconnect`: unlink the local `PaymentProfile` and
  delete/deauthorise the Stripe Express account.

## J. Avatar upload (GetPronto)

- `users/avatar.py`: presign + confirm upload, delete the previous file, store
  `profile_picture_url` / `profile_picture_getpronto_id`.
- Register an `image` `is_upload` form-field type + handler so an
  admin-authored profile form performs the upload. No new template.

## K. Connected-account webhooks

Handle **account-scoped** events (event carries `account`):

- `checkout.session.completed`, `payment_intent.succeeded`,
  `charge.refunded`, `charge.dispute.created`, `charge.dispute.closed`,
  `account.updated`.
- Ensure `payments/signals.py`, `meetings/signals.py` and `inbox/signals.py`
  sync from the connected account (`djstripe` `stripe_account`) so refunds and
  disputes started in a peer’s dashboard reflect on the platform.

## Migrations

- `core/0006` — Stripe settings fields.
- `peers/0005` — provider agreement fields + `terms_templates`.
- `users/0004` — `access_needs_templates`.
- No `accepted_tos` schema change.

## Admin Help (added to the Phase 10 seed)

Non-technical, high-school-level, well-formatted, idempotent:

1. **What each platform costs** — Stripe (card fees, Connect per-active-account,
   Stripe Tax 0.5%), Whereby, GetPronto, Daily, Hetzner, Tailscale, Cloudflare,
   GitHub, Coolify. Each row: what it does, how it’s charged, typical cost,
   pricing link, “prices change” note.
2. **How payments work here (the charge model)** — plain language + the table:
   destination vs **direct (chosen)** vs separate charges/transfers, covering
   merchant of record, who pays processing, platform fee, refunds/chargeback
   liability, platform maintenance, connect cost.
3. **Why we made these choices** — subscription gate, Express/KYC, provider
   agreement, refund policy, Stripe Tax, per-peer cart payment, direct charges.
4. **Managing money as a care provider** — the Express dashboard.
5. **Paying as a seeker** — book → pay → receipt → refunds.
6. **Accepting the Terms & Conditions (for admins)** — the
   `needs_tos_acceptance` audience, building an alert/page with `accept_tos`,
   and resetting acceptance (one user / audience / everyone).
7. Extend the existing refunds/fees/tax FAQ.

---

# Phase 8 — Blog, Contact and Host dashboard (admin-authored)

**Goal:** recreate the remaining mvp surfaces as admin-authored daisIE pages,
with app-side selectors and actions only.

- **Blog** — a `StandardPage`-based blog index + post detail (feeds and detail
  pages), admin-authored. No app models unless required.
- **Contact** — a `DaisieFormPage` contact form (topics as a small taxonomy or
  a choice list), admin-authored.
- **Host dashboard** — host-scoped context models (`host_requests`,
  `host_refunds`, `host_meetings`) and actions:
  - `bookings.approve`, `bookings.reject`, `bookings.revoke` (revoke-with-refund)
  - `refunds.approve`, `refunds.reject`
  Admin authors a `TabsBlock` for the actions with feeds as sibling blocks
  (feeds cannot nest in tabs). Approval actions flip the model flag so the
  existing daisIE approval signal runs.

**Testing:** refine existing action/selector tests; no new files.

---

# Phase 9 — Admin Help guide reader

**Goal:** read the Help snippets like a guide from the admin.

- Keep `HelpArticle` / `HelpCategory` / `GlossaryTerm` as **editable snippets**
  (already registered under the “Admin Guide” menu).
- Add a staff-only reader: `core/views/help.py` + one template, registered via
  `register_admin_urls`, a help-menu hook and a dashboard panel. Renders
  articles grouped by category (`body`/`steps` StreamFields).
- No schema change.

---

# Phase 10 — `seed_help_guide` command

**Goal:** ship initial, non-technical help content.

- Idempotent `get_or_create` management command (`get_or_create`, never
  clobbers edits).
- Seeds the five categories, the article set below, and Glossary terms —
  including **Stripe, Stripe Connect, Express dashboard, Whereby, GetPronto,
  Daily**, and the non-technical concepts (Project, Platform, Django, Wagtail,
  daisIE, Environment, Repository, Deployment, IaC, Ansible, GitHub, GitHub
  Actions, Coolify, Secrets, Bitwarden, Hetzner, Tailscale, Cloudflare, DNS,
  API key, webhook, OAuth, KYC, ICS, Tag group, Allowed tag, Taxonomy, etc.).
- Articles:
  1. What is NEUROMANCERS Network?
  2. Core concepts (Project, Platform, Django, Wagtail, Environment,
     Repository, Deployment, IaC, Ansible, GitHub, Coolify, Secrets, Hetzner).
  3. Search & filters.
  4. Tag groups vs allowed tags.
  5. Meeting links: group vs 1:1.
  6. Account (Allauth) emails vs notification emails.
  7. Editor quick-start (Operations menu).
  8. Infrastructure & deployments (operator guide) + the four operator Q&As.
  9. Getting help.
  10. **What each platform costs** (Phase 7 content).
  11. **How payments work here / charge model** (Phase 7 table).
  12. **Why we made these choices**.
  13. **Managing money as a care provider**.
  14. **Paying as a seeker**.
  15. **Accepting the Terms & Conditions (for admins)**.

**Testing:** idempotency verified by running the command twice.

---

# Phase 11 — `seed_pages` command (MVP-style pages)

**Goal:** pre-seed pages and chrome so the admin starts from an MVP-shaped site.

- Re-runnable `core/management/commands/seed_pages.py`; `--force` overwrites,
  otherwise only fills empty bodies. Runs after `core/0003_seed_chrome`.
- **Signed-in pages** are `core.StandardPage` with an `audience` block
  (`authenticated`) — no new page models:
  - `/settings` — `hero` + `tabs` (Account / Profile / Notifications /
    Calendar / Privacy(peer) / Payments(peer)), each an `action_form` bound to
    the matching `settings.*` action (Calendar and Payments completed in
    Phases 5/7).
  - `diary` — upcoming meetings calendar + bookings feed + cart “Pay all”.
  - `inbox` — notification feed + mark-read/delete actions.
  - `/meetings` — hero + published-meetings feed with Phase 1 filters; detail
    design via the shared `design_template`.
  - `/dashboard`, `/search` — shortcuts/feeds and search facets.
- **Feed snippets** (`wagtail_daisIE_feeds.Feed`) seeded by name:
  `meetings-published`, `bookings-upcoming`, `unpaid-bookings`,
  `notifications-user`, optional `reviews-published`.
- **Home chrome** — seed the home `hero` and the **Main navigation** / **Footer**
  menu bodies (`DaisyUIMenu`) with links to the seeded pages.
- Idempotent `get_or_create` for feeds/menus; `--force` to overwrite page
  bodies.

**Testing:** refine `core/tests/test_page_feeds.py` to assert the seeded feeds
resolve and the pages exist; idempotency verified by running twice.

---

# Appendix — verification and housekeeping

```sh
just manage makemigrations --check --noinput
just manage check
just pytest
just manage seed_help_guide && just manage seed_pages && just manage seed_pages
```

- All new admin surfaces are authored in the Wagtail admin; app code supplies
  only models, selectors, services, actions, form-field types and registries.
- Migrations are additive and committed per change.
- Refined tests only; redundant framework-level tests are removed.
