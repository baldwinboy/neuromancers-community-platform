# Implementation Audit - 2026-05-09

## Scope
This audit compares documented delivery claims against current repository evidence in `neuromancers_network`.

## Method
1. Reviewed planning docs (`ROADMAP.md`, `ARCHITECTURE.md`, `README.md`).
2. Verified claims against models, settings, routes, templates, CI workflows, and tests.
3. Classified status as Completed, Partial, Not Started, or Blocked.

## Current Status Snapshot

### Completed
- Core stack foundations are present: Django, Wagtail, Celery, Redis wiring, allauth, guardian, recurrence dependencies.
- CI pipeline and deployment workflows exist and execute lint/test/build/deploy stages.
- Infrastructure-as-code tree exists with concrete monitoring/security/backup/bootstrap files.
- Site lock feature is implemented with settings + middleware + lock template.
- Session data model foundations are substantial:
  - Peer and group session models
  - Pricing structures and validation
  - Session category model
  - Host availability rules
  - Review models
- Email template model and MJML client integration primitives are implemented.

### Partial
- Authentication hardening is partially implemented:
  - Login-by-code is enabled.
  - Rate limiting middleware/settings exist.
  - Signup form subclass exists, but does not currently add custom honeypot or extra validation logic.
- Profile/tier foundations are partial:
  - `Profile.tier_state` FSM exists.
  - Tier progression workflows and group-provisioning automation are not fully wired end-to-end.
- Session page routing exists but logic is incomplete and appears non-functional in current form:
  - Route handlers are scaffolded.
  - Routes render non-existent event templates.
  - Session model lookup map currently stores strings, not model classes.
- Notification architecture is partial:
  - Notification preferences field exists.
  - End-to-end dispatch logic honoring per-event preferences is not complete.

### Not Started / Missing
- End-to-end Stripe Checkout booking flow and webhook processing (claimed in docs) are not implemented in full.
- Calendar sync and export roadmap items are not implemented end-to-end.
- Moderation subsystem (flags, rules, automated moderation workflows) is not implemented.
- Private messaging and group chat models/workflows are not implemented.
- Comprehensive settings pages and user-facing templates for planned Day 2 pages are mostly absent.
- Rosetta i18n workflow and translated UI pipeline are not implemented.
- Auditlog integration is declared as dependency but not registered and wired.
- End-to-end coverage for events/core feature set remains limited.

## Documentation Drift Found
- `README.md` currently describes multiple features as fully implemented that are currently partial or missing (notably payments, calendar sync, messaging, and moderation).
- `ROADMAP.md` includes status notes that no longer consistently reflect repository evidence.

## Repository Health Risks
- Potential model export drift in core model namespace (`core/models/__init__.py` exports classes not present in current `core/models/pages.py`).
- Session routed page references templates that do not currently exist.
- Runtime validation was blocked in this audit context because required environment variables are not set (`DATABASE_URL` missing for `manage.py check`).

## Expert Checklist: What To Do Next

### Phase 1 - Correct Documentation and Baseline
1. Normalize `README.md` feature claims to match audited status (Completed vs Partial vs Planned).
2. Keep `ROADMAP.md` as source-of-truth planning, but add dated audit snapshot links.
3. Add a release-readiness section that gates release on payments, booking, notifications, and test coverage.

### Phase 2 - Stabilize Core Runtime Paths
1. Resolve core model export drift in `core/models/__init__.py` vs available page models.
2. Fix `SessionPage` model lookup and route handlers to use actual model classes.
3. Implement or remove route targets that currently point to missing templates.
4. Add smoke tests for all routed pages to prevent regressions.

### Phase 3 - Implement Booking + Payments Backbone
1. Implement canonical booking state machine for free and paid flows.
2. Build Stripe Checkout session creation and payment confirmation persistence.
3. Implement webhook verification and idempotent event processing.
4. Add tests for success, cancellation, retry, and refund paths.

### Phase 4 - Build User-Facing Session Experience
1. Implement session list/detail/create/edit templates and handlers.
2. Wire category filtering and host availability validation in booking forms.
3. Implement user dashboard views for host and attendee workflows.

### Phase 5 - Notifications and Email Completion
1. Implement `send_db_email` orchestration from template to MJML rendering to SMTP delivery.
2. Wire signals for booking, payment, reminder, and cancellation events.
3. Enforce notification preference controls in all dispatch paths.
4. Add admin preview workflow for transactional templates.

### Phase 6 - Calendar and Integrations
1. Implement `.ics` generation and export endpoints.
2. Add Google and Microsoft integration flows with background sync.
3. Add failure handling/retry policy and sync observability.

### Phase 7 - Moderation, Safety, and Ops Hardening
1. Add moderation data model (flags, statuses, actions).
2. Add moderator admin views and action flows.
3. Wire automated checks/rules only after manual moderation baseline is stable.
4. Add security and compliance verification checklist for production cutover.

### Phase 8 - Testing and Handover Quality Bar
1. Expand tests across events/core integrations and critical user journeys.
2. Add contract tests for webhook and external API boundaries.
3. Run coverage and define minimum threshold gates in CI.
4. Prepare technical handover docs tied to audited implementation state.
