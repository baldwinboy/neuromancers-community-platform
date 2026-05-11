## Plan: Sessions Flow Gap Closure

### Overarching Product Context — 20-Point Platform Flow

The platform is designed around 20 sequential user-facing capabilities. The session/payment flow (this plan's focus) maps to points **7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19**:

| # | Flow Point | Phase Mapping |
|---|-----------|---------------|
| 1 | Login-only landing for unauthenticated | Phase 5 (ops/infra) |
| 2 | Superuser login | Foundation (done) |
| 3 | Wagtail Admin `/cms/` | Foundation (done) |
| 4 | Branding, API keys, AllAuth theme | Foundation (done) |
| 5 | Initial pages + admin checklist | Phase 2 (admin guardrails) |
| 6 | Block branding inheritance | Foundation (done) |
| 7 | **Standard + model-connected forms** | **Phase 2** (form execution layer) |
| 8 | Admin-editable email content (MJML) | Phase 5 (notifications) |
| 9 | Standard user login + verification | Foundation (done) |
| 10 | **Attribute blocks for model content** | **Phase 2** (detail rendering) |
| 11 | **Index pages with model layout blocks** | **Phase 2** (model layouts) |
| 12 | **Session detail pages** | **Phase 3** (session routes) |
| 13 | **User profile pages** | **Phase 3** (profile routes) |
| 14 | Admin-configured settings pages | Phase 5 (auth) |
| 15 | **Session detail with conditional buttons** | **Phase 3** (booking/pay routes) |
| 16 | Schedule page with calendar block | Phase 6 (calendar) |
| 17 | **Host Stripe Connect onboarding** | **Phase 4** (payments) |
| 18 | **Peer subscription via Stripe** | **Phase 4** (subscriptions) |
| 19 | **Webhook setup via Wagtail admin** | **Phase 4** (webhooks) |
| 20 | Navbar customization | Foundation (done) |

### Current Codebase State

**What exists and works:**
- Full block system (`common/blocks/`) — 50+ content/field block types
- `form_fields.py` — 14 standard form field blocks, FormBlock (clean, no model mapping)
- `modelform_fields.py` — 14 model-mapped field blocks, ModelFormBlock, ContentModelFormBlock
- `StyledPageMixin` + `StyledFormPageMixin` for page-level styling
- Site-wide settings: branding, API keys, site lock, navbar, footer, allauth
- Full event domain models in `events/models/base.py`: Session, SessionBooking, SessionPrice, SessionSeries, Review, AvailabilityRule, DurationPrice, WebhookEventLog
- Booking/payment FSM with all canonical transitions
- Full Stripe Connect integration: OAuth onboarding, account status, checkout creation, webhook processing with idempotency
- Charge-routing policy (`events/checkout.py`): destination charges for single bookings, separate charges for multi-session carts
- Publish gating: `Session.clean()` requires Stripe account for paid sessions
- Form execution layer (`common/binder.py`): ModelFormBinder with create/update/delete, allowlists, ownership checks, autofill
- Detail rendering: AttributeBlock in content.py, model_form_fields API endpoint
- SessionPage route handlers (618 lines) — all routes implemented with proper handlers and templates
- 14 session templates with full HTML content (DaisyUI)
- User profile template (`templates/users/profile.html`)
- Home (`home.html`) and About (`about.html`) templates
- EmailTemplate model + `_block_to_mjml()` method
- Bootstrap admin guide command — all 4 markdown source files present
- Database migrations for core (0001), events (0001-0004), and emails (0001)
- Tests (789 lines, 12 test classes): state transitions, availability, overlap, capacity, checkout strategy, webhooks, transfer planning
- Wagtail admin hooks: model_form_fields API endpoint registered
- CI/CD pipeline, IaC directory, pre-commit hooks

**What remains (Phase 6 and beyond):**
- Calendar sync (Google, Microsoft, iCloud) — dependencies declared, not wired
- Admin analytics
- Waitlist and cancellation flows
- Peer subscription flow via Stripe
- WCAG 2.1 AA audit
- Performance profiling

### Phases

1. Phase 1: Formalize domain contracts and state model.
2. Define canonical booking/payment statuses and transitions for peer/group sessions, including pending approval, payment required, confirmed, cancelled, completed, and failed/expired payment. *blocks steps 3-10*
3. Define charge-routing policy for mixed checkout: single-session direct pay uses destination charges; multi-session cart pay uses separate charges and transfers with transfer grouping and transfer creation policy. Include cross-host checkout rule and failure fallback. *blocks steps 7-8*
4. Define publish gating policy: free sessions can publish without Stripe account; paid sessions require connected account readiness checks.

**Phase 1 Deliverables (Specification)**
1. Domain contracts document finalized and approved.
2. Booking and payment state enums finalized and mapped to persistence fields.
3. State transition matrix finalized with event triggers, guards, and side effects.
4. Charge-routing policy finalized for single-session and multi-session checkout.
5. Publish gating policy finalized for free vs paid sessions.

**Phase 1A: Canonical Domain Contracts**
Status (2026-05-11): Phase 1A spec is fully implemented. Event models consolidated into `events/models/base.py`.
1. Implemented in code:
	- booking canonical fields and enums on SessionBooking
	- Stripe connected account persistence via FK to djstripe.Account (User.stripe_account)
	- canonical booking status usage in booking constraints and auto-approval signals
	- all event domain models (Session, SessionBooking, SessionPrice, SessionSeries, Review) in `base.py`
	- charge-routing policy (`events/checkout.py`) and publish gating (`Session.clean()`)
2. Remaining for Phase 1A closure:
	- align session contract documentation to exact persisted field names where currently class-derived

1. Booking domain entity contract:
	- identity: booking_id, session_id, attendee_id, host_id
	- timing: starts_at, ends_at, timezone
	- workflow: booking_status, payment_status, approval_required
	- money: amount_due_subunit, amount_paid_subunit, currency, checkout_reference
	- audit: created_at, updated_at, transition_log
2. Session domain entity contract:
	- identity: session_id, session_type (peer|group), host_id
	- publication: is_published, visibility
	- payment policy: require_payment_before_joining
	- approval policy: require_approval, require_refund_approval
	- constraints: capacity (group), min/max duration (peer), availability rules (peer)
3. Stripe account contract:
	- identity: user_id, stripe_account (FK to djstripe.Account)
	- readiness: derived from Stripe API Account retrieval (charges_enabled, payouts_enabled, details_submitted)
	- onboarding: managed via Stripe Connect OAuth flow

**Phase 1B: Canonical Status Model**
1. Booking status (business lifecycle):
	- pending_approval: request received and awaiting host/admin approval
	- approved: approved but not yet joinable unless payment rules are satisfied
	- confirmed: fully scheduled and joinable according to policy
	- cancelled: booking cancelled by attendee/host/admin
	- completed: session finished and closed
	- expired: request or payment window timed out
2. Payment status (financial lifecycle):
	- not_required: free session or no payment required
	- required: payment needed before confirmation/join
	- checkout_created: checkout session created and awaiting completion
	- processing: asynchronous payment confirmation in progress
	- paid: payment succeeded
	- failed: payment failed
	- refunded: full refund completed
	- refund_pending_approval: refund requested and awaiting approval
3. Derived rule for scheduling:
	- can_join = booking_status == confirmed AND payment_status IN (not_required, paid)

**Phase 1C: State Transitions (Source of Truth)**
1. Booking creation:
	- if require_approval = true: booking_status = pending_approval
	- if require_approval = false and payment not required: booking_status = confirmed, payment_status = not_required
	- if require_approval = false and payment required: booking_status = approved, payment_status = required
2. Approval path:
	- pending_approval -> approved on host/admin approve action
	- approved -> confirmed only when payment_status IN (not_required, paid)
3. Payment path:
	- required -> checkout_created on pay action
	- checkout_created -> processing on checkout.session.completed (if async)
	- checkout_created|processing -> paid on async success/success event
	- checkout_created|processing -> failed on async failure event
	- paid + approved -> confirmed
4. Cancellation and completion:
	- pending_approval|approved|confirmed -> cancelled on cancel action
	- confirmed -> completed on session end workflow
5. Expiry:
	- pending_approval -> expired after approval timeout
	- checkout_created|processing -> expired after payment timeout

**Phase 1D: Charge-Routing Policy**
1. Single unpaid session checkout:
	- use destination charges
	- set transfer_data.destination to host connected account
	- set application_fee_amount according to platform fee policy
2. Multi-session checkout (/pay cart):
	- use separate charges and transfers
	- create one platform charge with transfer_group
	- create deterministic transfers per selected booking item
3. Cross-host carts:
	- allowed
	- each selected booking must map to one destination transfer in settlement ledger
4. Failure fallback:
	- if transfer creation partially fails, booking statuses remain non-confirmed and are marked for retry workflow

**Phase 1E: Publish Gating Policy**
1. Free sessions:
	- may publish without Stripe connected account
2. Paid sessions:
	- may publish only if host has Stripe account with readiness checks passing
3. Readiness checks for paid publish:
	- user.stripe_account is not None (FK to djstripe.Account)
	- Stripe API Account.charges_enabled, Account.payouts_enabled, Account.details_submitted
	- capability to receive transfers is active

**Phase 1F: Invariants and Guard Conditions**
1. A booking cannot be confirmed if pricing is required and payment is not paid.
2. A booking cannot transition from cancelled/completed/expired back to confirmed.
3. A group booking cannot be confirmed when capacity is exhausted.
4. A peer booking cannot be confirmed when time overlap or duration constraints fail.
5. If no host availability rules exist, peer host availability defaults to 24/7.
6. All status transitions must be idempotent and auditable.

**Phase 1G: Acceptance Criteria**
1. Status enums and transition table are documented in code-facing specification and mirrored in tests.
2. Every transition has a trigger, guard, and side effect defined.
3. Payment routing decision is deterministic for single vs multi selection in /pay.
4. Publish gating behavior is explicitly testable for free and paid sessions.
5. Phase 2 can start without re-opening domain terminology or status semantics.

5. Phase 2: Wagtail-model binding architecture. **FULLY IMPLEMENTED** — see `common/binder.py` (295 lines).
6. Implement model-aware form execution layer that consumes existing field blocks (from `modelform_fields.py`) and maps cleaned form values to model fields safely, including defaults/autofill fields (host, timestamps, ownership). *done*
7. Implement detail binding contract for model field rendering blocks so admin-selected model attributes render predictably from route context. *done*
8. Add admin guardrails in block editors: model selector, field chooser, incompatible-type warnings, required mapping hints, and JSON field handling policy (serialize/deserialize/unsupported type messaging). *done — validation in ModelFormBlock.clean() and binder checks*
9. Add UX-safe fallback behavior when no model is selected (standard form behavior with no mapping), and explicit validation errors when mapping is partially configured. *done — `_handle_no_model()` in binder*

**Phase 2 Deliverables (Architecture + Contracts)** — All implemented.

**Phase 2A: Binding Architecture Overview** — Implemented.
1. Binding roles:
	- form schema role: Wagtail blocks define user-visible fields, help text, and validation hints
	- binding role: each bindable block optionally maps to one model + one model field
	- execution role: a server-side binder validates and persists values to model instances
	- rendering role: detail blocks resolve and display model attributes using route context
2. Binding scopes:
	- create scope: instantiate model object and apply mapped values
	- update scope: load target model object and apply mapped values with authorization checks
	- delete scope: execute model deletion via explicit action block and confirmation rules
3. Safety baseline:
	- block configuration must never directly grant write access to disallowed model fields
	- all writes must pass a server-side allowlist
	- all reads must pass object-level permission checks

**Phase 2B: Form Execution Contract** — Implemented in `ModelFormBinder.execute()`.
1. Submission pipeline contract:
	- parse block schema -> build runtime form -> clean values -> map fields -> persist atomically
2. Mapper input contract:
	- page_id, route_name, action_type (create|update|delete), user_id, target_model, target_object_id(optional), cleaned_form_data
3. Mapper output contract:
	- success/failure result, instance_id(optional), field_errors, non_field_errors, transition_events(optional)
4. Field mapping contract:
	- only fields in model allowlist can be mapped
	- one form field maps to at most one model field
	- duplicate mappings to the same model field are rejected at validation time
5. Autofill contract (non-user editable by default):
	- host/owner fields derive from authenticated user
	- created_at/updated_at remain model-managed
	- status defaults derive from Phase 1 state policy, not from free-form input
6. Atomicity contract:
	- mapping and persistence run inside one transaction for each submission
	- partial writes are disallowed on mapper failure

**Phase 2C: Detail Rendering Contract** — AttributeBlock + model_form_fields API endpoint.
1. Context resolution order contract:
	- explicit context object from route handler
	- page-bound object
	- fallback object map by model key
2. Attribute resolution contract:
	- only configured model + field pair is resolved
	- unknown fields render a safe placeholder for admins and nothing for public users
3. Visibility contract:
	- block-level visibility rules are enforced before attribute resolution
	- private attributes require explicit allowlist and owner/admin permission
4. Format contract:
	- scalar values render as text
	- datetime values render in user/session timezone policy
	- rich text fields render sanitized output

**Phase 2D: Admin Guardrails in Block Editors** — Implemented in `ModelFormBlock.clean()` and `ModelFormBinder._build_runtime_form()`.

**Phase 2E: No-Model and Partial-Mapping Behavior** — Implemented in `binder.py`.

**Phase 2F: JSON Field Handling Policy** — Implemented: `_coerce_json()` in binder.

**Phase 2G: Permissions and Security Contract** — Implemented: `_check_ownership()`, `MODEL_ALLOWLISTS`, `BLOCKED_FIELDS`.

**Phase 2H: Performance and Caching Contract** — `_get_block_class()` uses `@cache`.

**Phase 2I: Acceptance Criteria** — All 8 criteria met by binder.py + tests.

10. Phase 3: Session routes and form handling. **FULLY IMPLEMENTED** — see `events/models/pages.py` (618 lines) + 14 templates.
11. Replace session/create/edit/delete/booking/payment route stubs with real handlers and permission checks (owner/staff/public visibility) and explicit 403/404 behavior. *done*
12. Implement peer availability flow using weekly rules plus user-friendly calendar-range UI for input; enforce no-rules-means-24/7. *done*
13. Enforce booking-time checks: duration constraints, host overlap, group capacity, and availability window validation using timezone-aware logic. *done*
14. Add optimistic+DB-level concurrency protections for race conditions around last capacity slot and overlapping time bookings. *done — select_for_update in book route*

**Phase 3 Deliverables (Routes + Execution)** — All implemented.

**Phase 3A: Route Surface and Canonical Endpoints**
1. Session routes:
	- `/sessions/<session_id>/` — detail view
	- `/sessions/<session_id>/edit/` — edit view
	- `/sessions/<session_id>/delete/` — delete view
	- `/sessions/<session_id>/book/` — booking view
	- `/sessions/<session_id>/pay/` — payment view
	- `/sessions/<session_id>/cancel/` — cancel booking
	- `/sessions/<session_id>/reschedule/` — reschedule
	- `/sessions/<session_id>/feedback/` — feedback/review
	- `/sessions/<session_id>/reviews/` — reviews listing
	- `/sessions/<session_id>/participants/` — host participants
	- `/sessions/<session_id>/booking/<booking_id>/approve/` — host approve
	- `/sessions/bookings/` — host bookings dashboard
	- `/sessions/availability/` — host availability CRUD
	- `/sessions/availability/<rule_id>/delete/` — delete availability rule

**Phase 3B-3K**: [Contracts remain valid as written; all routes implemented.]

15. Phase 4: Payment orchestration and webhooks. **FULLY IMPLEMENTED** — see `events/views/stripe.py` (310 lines) + `events/checkout.py` (234 lines).
16. Implement /pay programmatic endpoint with deterministic checkout request building for single vs multi unpaid sessions. *done*
17. Implement Stripe connected-account persistence and onboarding flow, including Account Link creation and account status retrieval. *done*
18. Implement webhook ingestion with signature verification, idempotent event processing, retries, and dead-letter handling. *done*
19. Implement post-payment status transition logic for success/failure/async outcomes, including transfer creation logic. *done*

**Phase 4 Deliverables** — All implemented.

**Phases 4A-4L**: [Detailed contracts remain valid as written; all implemented.]

20. Phase 5: Safety, usability, and operations.
21. Add anti-IDOR authorization checks across all routes and model actions.
22. Add accessibility and user guidance pass: plain-language labels/help texts, validation copy, keyboard navigation, and screen-reader behavior.
23. Add observability and support tools: structured logs, audit records, admin troubleshooting views.
24. Add migration/backfill strategy for existing sessions/bookings and rollback path for deployment safety.

**Phase 5 Deliverables** — Partially done: ownership checks on routes and binder; structured logging via logger; no dedicated audit log integration.

**Phases 5A-5I**: [Detailed contracts remain valid as written.]

25. Phase 6: Verification and hardening.
26. Add tests for mapping correctness, state transitions, approval/payment edge cases, availability/timezone behavior, webhook idempotency, and concurrency.
27. Run end-to-end smoke flows for create/edit/delete, booking pending approval, free auto-schedule, paid payment-required then confirm, and multi-session mixed-host checkout.
28. Conduct security and data integrity review.

**Phase 6 Deliverables** — Tests exist (789 lines, 12 classes); end-to-end smoke flows pending manual verification.

**Relevant files** (updated for current codebase state)
- `/Users/giraffe/neuromancers_network/neuromancers_network/common/blocks/modelform_fields.py` — model-mappable field blocks, ModelFormBlock with validation guardrails.
- `/Users/giraffe/neuromancers_network/neuromancers_network/common/blocks/form_fields.py` — standard form fields (clean, no model mapping).
- `/Users/giraffe/neuromancers_network/neuromancers_network/common/blocks/content.py` — AttributeBlock and permission metadata for detail rendering.
- `/Users/giraffe/neuromancers_network/neuromancers_network/common/binder.py` — ModelFormBinder: form execution layer with create/update/delete, allowlists, ownership checks, autofill, JSON coercion.
- `/Users/giraffe/neuromancers_network/neuromancers_network/common/views.py` — model_form_fields API endpoint for Ajax field chooser.
- `/Users/giraffe/neuromancers_network/neuromancers_network/common/wagtail_hooks.py` — Admin URL registration for field chooser API.
- `/Users/giraffe/neuromancers_network/neuromancers_network/events/models/pages.py` — SessionPage with all route handlers (618 lines).
- `/Users/giraffe/neuromancers_network/neuromancers_network/events/models/base.py` — all event domain models (Session, SessionBooking, SessionPrice, SessionSeries, Review, AvailabilityRule, DurationPrice, WebhookEventLog), booking/payment enums, FSM transitions, pricing validation, overlap checks, publish gating.
- `/Users/giraffe/neuromancers_network/neuromancers_network/events/checkout.py` — charge-routing policy: CheckoutStrategy, destination/separate charges, transfer planning, platform fee calculation.
- `/Users/giraffe/neuromancers_network/neuromancers_network/events/views/stripe.py` — Stripe onboarding, account status, checkout creation, webhook handlers with idempotency (310 lines).
- `/Users/giraffe/neuromancers_network/neuromancers_network/common/stripe.py` — Stripe helper: OAuth, account readiness checks.
- `/Users/giraffe/neuromancers_network/neuromancers_network/events/signals.py` — booking creation signal logger.
- `/Users/giraffe/neuromancers_network/neuromancers_network/events/templates/events/` — 14 session templates (detail, base, booking, payment, cancel, reschedule, edit, delete, feedback, reviews, participants, bookings, availability, availability_delete).
- `/Users/giraffe/neuromancers_network/config/urls.py` — registered webhook/pay/onboarding endpoints.
- `/Users/giraffe/neuromancers_network/neuromancers_network/events/tests.py` — 789 lines, 12 test classes covering state transitions, availability, overlap, capacity, checkout strategy, webhooks, transfer planning.
- `/Users/giraffe/neuromancers_network/neuromancers_network/emails/models.py` — EmailTemplate model + `_block_to_mjml()` method.
- `/Users/giraffe/neuromancers_network/neuromancers_network/core/management/commands/bootstrap_admin_guide.py` — seed command with 4 markdown source files present.

**Verification** — [specifications remain valid as written].

**Decisions** — [remain valid].

**Further Considerations** — [remain valid].

### Known Remaining Gaps (Post-Audit)

| Area | Status | Notes |
|------|--------|-------|
| Calendar sync | ❌ Not started | Dependencies declared; Google, Microsoft, iCloud |
| Admin analytics | ❌ Not started | Charts in Wagtail dashboard |
| WCAG 2.1 AA audit | ❌ Not started | Automated + manual audit |
| Performance profiling | ❌ Not started | Query optimisation, caching tuning |

### Recently Closed Gaps (2026-05-11)

| Area | Status | Implementation |
|------|--------|----------------|
| Moderation | ✅ Done | `moderation/` app: Flag, FlagRule models + admin actions |
| Private messaging | ✅ Done | `messaging/` app: Conversation, Message models + inbox views/templates |
| Allauth template restyling | ✅ Done | All allauth templates converted from Bootstrap to DaisyUI |
| Notification dispatch | ✅ Done | `events/signals.py` wired to Celery tasks for booking/payment/review events |
| `send_db_email` utility | ✅ Done | `emails/utils.py`: renders EmailTemplate → MJML API → SMTP delivery |
| MJML base template | ✅ Done | `templates/emails/layout.mjml` with header/footer/divider |
| Celery beat tasks | ✅ Done | `events/tasks.py`: reminders, review prompts, stale booking expiry |
| i18n | ✅ Done | django-rosetta installed, LANGUAGES configured, URLs registered |
| GDPR automation | ✅ Done | `anonymize_user` management command for data erasure |
| Audit log wiring | ✅ Done | django-auditlog registered on Session, SessionBooking, SessionPrice, Review |
| Security hardening | ✅ Done | CSP middleware, HSTS/security-headers middleware, Permissions-Policy |

### Today's Newly Completed Items (2026-05-11)

| Area | Status | Implementation |
|------|--------|----------------|
| Admin settings pages | ✅ Done | UserProfilePage settings routes + UserSettings toggles for password/email/notifications/profile |
| Schedule / calendar page | ✅ Done | `/sessions/calendar/` route with month grid template in SessionPage |
| Peer subscription via Stripe | ✅ Done | StripeSubscriptionCheckoutView + webhook tier promotion/demotion |
| Email preview in Wagtail admin | ✅ Done | EmailTemplateViewSet with PreviewableMixin, inspect + preview views |
| AllAuth email customization | ✅ Done | AccountAdapter.send_mail() → send_db_email + EmailTemplate models for login_code/verification/password_reset etc. |

| Area | Status | Implementation |
|------|--------|----------------|
| Moderation | ✅ Done | `moderation/` app: Flag, FlagRule models + admin actions |
| Private messaging | ✅ Done | `messaging/` app: Conversation, Message models + inbox views/templates |
| Allauth template restyling | ✅ Done | All allauth templates converted from Bootstrap to DaisyUI |
| Notification dispatch | ✅ Done | `events/signals.py` wired to Celery tasks for booking/payment/review events |
| `send_db_email` utility | ✅ Done | `emails/utils.py`: renders EmailTemplate → MJML API → SMTP delivery |
| MJML base template | ✅ Done | `templates/emails/layout.mjml` with header/footer/divider |
| Celery beat tasks | ✅ Done | `events/tasks.py`: reminders, review prompts, stale booking expiry |
| i18n | ✅ Done | django-rosetta installed, LANGUAGES configured, URLs registered |
| GDPR automation | ✅ Done | `anonymize_user` management command for data erasure |
| Audit log wiring | ✅ Done | django-auditlog registered on Session, SessionBooking, SessionPrice, Review |
| Security hardening | ✅ Done | CSP middleware, HSTS/security-headers middleware, Permissions-Policy |
