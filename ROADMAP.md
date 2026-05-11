# NEUROMANCERS Network — Implementation Roadmap

## Platform Flow (Product Requirements)

The platform is designed around 20 sequential user-facing capabilities. This roadmap is organized to deliver these flows in implementation phases, not necessarily in their numbered order.

| # | Flow Point | Phase | Status |
|---|-----------|-------|--------|
| 1 | Login-only landing for unauthenticated users | A | 🔶 Partial — SiteLock middleware exists; no unconditional login redirect |
| 2 | Superuser login | A | ✅ Done — allauth at `/login/`, Wagtail admin at `/cms/` |
| 3 | Wagtail Admin dashboard (`/cms`) | A | ✅ Done — routed, slug validation, admin guide |
| 4 | Superuser prepares branding, API keys, AllAuth theme | A | ✅ Done — SiteDesignSettings, ExternalAPISettings, AllAuthSettings all exist |
| 5 | Create initial pages + admin checklist | A | ✅ Done — admin guide model + bootstrap command + 4 markdown source files exist |
| 6 | Blocks inherit branding styling | A | ✅ Done — StyledPageMixin + CSS custom properties + daisyui theme |
| 7 | Standard forms + model-connected forms | B | ✅ Done — form_fields.py + modelform_fields.py + modelform binder execution layer |
| 8 | Admin-editable email content (MJML) | B | ✅ Done — EmailTemplate model + _block_to_mjml() + send_db_email + MJML base layout |
| 9 | Standard user login + email verification | A | ✅ Done — allauth email verification, login-by-code, custom signup form |
| 10 | Attribute blocks for dynamic model content | B | ✅ Done — AttributeBlock + model_form_fields API + binder detail binding |
| 11 | Index pages with model layout blocks | C | ✅ Done — RowBlock, ColumnBlock, GridBlock exist |
| 12 | Session detail pages (`/sessions/<uuid>/`) | C | ✅ Done — SessionPage with 14 route handlers and 14 templates |
| 13 | User profile pages (`/users/<username>/`) | C | ✅ Done — UserProfilePage exists + profile template |
| 14 | Admin-configured settings pages | C | ✅ Done — UserProfilePage settings routes + UserSettings toggles |
| 15 | Session detail with conditional buttons | C | ✅ Done — booking/pay/cancel/reschedule/feedback routes with host/attendee conditional UI |
| 16 | Schedule page with calendar block | D | ✅ Done — `/sessions/calendar/` route with month grid template |
| 17 | Host Stripe Connect onboarding | D | ✅ Done — OAuth onboarding, account status, checkout creation, webhook processing |
| 18 | Peer subscription via Stripe | D | ✅ Done — StripeSubscriptionCheckoutView + webhook tier promotion/demotion |
| 19 | Webhook setup via Wagtail admin | D | ✅ Done — StripeWebhookView with idempotency + dj-stripe admin URLs |
| 20 | Navbar customization | A | ✅ Done — wagtailmenus + NavbarSettings + NavbarDesignBlock |

---

## Phase A: Foundation & Block System ✅ (Complete)

| # | Task | Status |
|---|------|--------|
| A.1 | Project generation (cookiecutter-django) + Wagtail 7.x integration | ✅ |
| A.2 | Core design system (daisyui palette, typography, backgrounds) | ✅ |
| A.3 | StyledPageMixin — per-page styling with CSS custom properties | ✅ |
| A.4 | Site-wide settings: branding, external APIs, site lock, content, navbar, footer, allauth | ✅ |
| A.5 | Wagtail admin customization: slug validation, admin guide, onboarding checklist | ✅ |
| A.6 | Celery + Redis configuration | ✅ |
| A.7 | CI/CD pipeline: GitHub Actions → Ansible → Coolify | ✅ |
| A.8 | IaC directory: monitoring, security, backups, bootstrap scripts | ✅ |
| A.9 | Site lock middleware + template | ✅ |
| A.10 | Content block system (50+ blocks): backgrounds, buttons, cards, accordions, grids, etc. | ✅ |
| A.11 | Form field blocks: 14 field types, layouts, steps, success handling | ✅ |
| A.12 | Model-mapped form field blocks: modelform_fields.py with ModelMappableFieldBlock | ✅ |
| A.13 | Update `form_fields.py` — remove model mapping, clean FormBlock | ✅ |
| A.14 | Fix pre-existing import bugs blocking Django startup | ✅ |

---

## Phase B: Auth, Pages & Admin Experience ✅ (Complete)

| # | Task | Status |
|---|------|--------|
| B.1 | AllAuth theme templates — convert from Bootstrap to Tailwind/DaisyUI | ✅ Done |
| B.2 | Login-only landing for unauthenticated users | 🔶 Partial — SiteLock exists but no unconditional redirect |
| B.3 | Bootstrap/setup management command — create HomePage, initial content, default pages | ✅ Done — admin_guide bootstrap command works with 4 markdown files |
| B.4 | Admin guide markdown source files | ✅ Done — all 4 files exist in core/admin_guide/ |
| B.5 | EmailTemplate model completion: implement `_block_to_mjml()` | ✅ Done — method implemented for heading/paragraph/button/divider/image/spacer |
| B.5b | EmailTemplate migrations | ✅ Done — emails/migrations/0001_initial.py exists |
| B.6 | MJML base layout template (`templates/emails/layout.mjml`) | ✅ Done |
| B.7 | Email preview page in Wagtail admin | ❌ Not started |
| B.8 | `send_db_email` implementation — template → MJML render → SMTP delivery | ✅ Done — `emails/utils.py` |
| B.9 | Wire notification signals for core events (booking, payment, tier change) | ✅ Done — `events/signals.py` → Celery tasks |
| B.10 | User-facing page templates: home, about | ✅ Done — home.html and about.html exist in templates/pages/ |
| B.11 | Event models (consolidated in base.py) | ✅ Done — Session, SessionBooking, SessionPrice, SessionSeries, Review, AvailabilityRule, DurationPrice, WebhookEventLog |
| B.12 | Event model __init__.py with correct imports | ✅ Done — all imports from base.py |
| B.13 | Event model migrations | ✅ Done — 4 migrations in events/migrations/ |

---

## Phase C: Session Models, Routes & Forms ✅ (Complete)

| # | Task | Status |
|---|------|--------|
| C.1 | Session/booking models with FSM | ✅ Done — all in base.py with full state transitions |
| C.2 | Session page templates (14 templates) | ✅ Done — all with full DaisyUI HTML |
| C.3 | User profile template (`users/profile.html`) | ✅ Done |
| C.4 | SessionPage route handlers — 14 routes | ✅ Done — full implementation with permission checks |
| C.5 | UserProfilePage route handlers | ✅ Done |
| C.6 | Standard form submission handler | ✅ Done — binder handles no-model forms |
| C.7 | Model form execution layer | ✅ Done — common/binder.py (295 lines) |
| C.8 | Attribute block route-context binding | ✅ Done — AttributeBlock + model_form_fields API |
| C.9 | Session index page with model layout blocks | ✅ Done — grid/row/column blocks exist |
| C.10 | Admin-configured settings pages replacing AllAuth defaults | ✅ Done — UserProfilePage settings routes + UserSettings toggles |

---

## Phase D: Booking, Payments & Stripe Connect ✅ (Complete)

| # | Task | Status |
|---|------|--------|
| D.1 | Canonical booking status FSM (pending_approval → confirmed → cancelled → completed) | ✅ Done — FSMField with 6 transitions on SessionBooking |
| D.2 | Payment status FSM (not_required → required → paid → refunded) | ✅ Done — FSMField with 8 transitions on SessionBooking |
| D.3 | Stripe Checkout session creation views | ✅ Done — StripeCheckoutView + page-level pay route |
| D.4 | Stripe webhook verification + idempotent event processing | ✅ Done — StripeWebhookView with WebhookEventLog |
| D.5 | /pay programmatic endpoint (single vs multi-session) | ✅ Done — determine_strategy() + build_destination/separate_charges_params |
| D.6 | Stripe Connect onboarding flow (Account Link, status retrieval) | ✅ Done — StripeOnboardingView + CallbackView + AccountStatusView |
| D.7 | Post-payment status transition logic | ✅ Done — mark_paid transitions + _handle_checkout_completed |
| D.8 | Refund processing (auto-refund vs pending-approval) | ✅ Done — request_refund / auto_refund / approve_refund FSM transitions |
| D.9 | Free session auto-confirm (skip Stripe, instant confirmation) | ✅ Done — SessionBooking.save() sets NOT_REQUIRED when amount is 0; booking flow auto-confirms |
| D.10 | Multi-session cart booking flow | ✅ Done — separate charges strategy + plan_transfers + _execute_transfers |

---

## Phase E: Email, Notifications & MJML 🔶 (Mostly Complete)

| # | Task | Status |
|---|------|--------|
| E.1 | Complete EmailTemplate.model (`_block_to_mjml()` method) | ✅ Done |
| E.2 | Create MJML templates (base layout, header, footer, content blocks) | ✅ Done — `templates/emails/layout.mjml` |
| E.3 | Implement `send_db_email` utility (template → MJML API → SMTP) | ✅ Done — `emails/utils.py` |
| E.4 | Wire notification signals: account, session, payment, reminder events | ✅ Done — `events/signals.py` → Celery tasks |
| E.5 | Implement notification preference dispatch logic | 🔶 Partial — field exists; dispatch not wired |
| E.6 | Email preview page in Wagtail admin | ✅ Done — EmailTemplateViewSet with inspect + preview views |
| E.7 | Celery beat tasks: 24h/1h reminders, post-session review prompt | ✅ Done — `events/tasks.py` + CELERY_BEAT_SCHEDULE |
| E.8 | AllAuth email customization (login code, verification, password reset) | ✅ Done — AccountAdapter.send_mail() → send_db_email + EmailTemplate models |

---

## Phase F: Calendar, Moderation & Production Hardening 🔶 (Mostly Complete)

| # | Task | Status |
|---|------|--------|
| F.1 | `.ics` export for sessions | ❌ |
| F.2 | Google Calendar sync (OAuth, push, free/busy) | ❌ |
| F.3 | Microsoft Graph sync | ❌ |
| F.4 | iCloud CalDAV free/busy read | ❌ |
| F.5 | Calendar connection settings UI | ❌ |
| F.6 | Moderation: Flag model, FlagRule, admin actions | ✅ Done — `moderation/` app |
| F.7 | Private messaging (Conversation, Message, inbox) | ✅ Done — `messaging/` app |
| F.8 | Group chat (SessionThread for group sessions) | ❌ |
| F.9 | Audit log integration (django-auditlog) | ✅ Done — registered on Session, SessionBooking, SessionPrice, Review |
| F.10 | i18n (django-rosetta, language switcher) | ✅ Done — LANGUAGES configured, URLs registered |
| F.11 | Admin analytics dashboard | ❌ |
| F.12 | Waitlist and cancellation flows | ❌ |
| F.13 | GDPR automation (anonymization, data export) | ✅ Done — `anonymize_user` management command |
| F.14 | Schedule page with calendar block | ✅ Done — `/sessions/calendar/` route + month grid |
| F.15 | Peer subscription flow via Stripe | ✅ Done — StripeSubscriptionCheckoutView + webhook handlers |
| F.16 | WCAG 2.1 AA audit and fixes | ❌ |
| F.17 | Performance profiling and optimisation | ❌ |
| F.18 | Security hardening (CSP, HSTS, rate limiting) | ✅ Done — CSP middleware, HSTS headers, Permissions-Policy |

---

## Handover Criteria

- All 20 platform flow points functional and tested
- WCAG 2.1 AA level confirmed by automated tools and spot-checks
- GDPR data retention automation active
- Admin users can view analytics, impersonate users, and modify all site terminology
- Admins can edit email subject/body via Wagtail and preview emails
- Infrastructure configuration stored in `iac/` directory; CI/CD uses Coolify API for deployment
- Production environment stable on **Coolify + Hetzner**

---

## Audit Snapshot

- Latest implementation audit: `docs/implementation-audit-2026-05-09.md`
- Use that audit as the current reality baseline
- This roadmap remains the planning artifact; the audit document is the evidence artifact
