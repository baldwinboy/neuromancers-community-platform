# NEUROMANCERS Network — Roadmap

> Status: prior work committed. This roadmap is the ordered, step-by-step path to
> bring the platform to full functionality. It begins with a blocking
> correctness/security phase, then the planned feature work (A–D).

## Principles

- App code owns models, selectors, services, actions, registries; **all UI is
  authored in the Wagtail admin**.
- **Reuse, don't re-implement** (`search_*`, `create_booking`, daisIE context
  models/filters/actions/blocks, Stripe/dj-stripe, inbox bus, daisIE form pages).
- **Production-grade only**: KISS, DRY, SOLID, YAGNI. No speculative abstraction.
- **No regressions**: every fix/feature ships with tests; `makemigrations
  --check` stays clean; additive schema only.
- **Bug fixes are test-first**: reproduce with a failing test, then fix.
- **Tests assert behaviour, not implementation details**: prefer outcomes
  (statuses, amounts, errors, guards) over mocked call kwargs, exact metadata
  strings or internal call counts; pure helpers get no-database tests. Keep
  DB-backed suites lean (they are the slow ones).
- Failures are explicit and logged with context; no silent fallbacks.
- Long-running/environment-sensitive commands are **handovers** owned by the human
  or CI (`docker`, long `just` recipes, `uv sync/lock`, full `pytest`,
  `manage.py migrate/collectstatic/loaddata/rebuild_index/update_index`,
  `ansible-playbook`, `clientele` regen).

## Verification (run after each change)

```sh
just manage makemigrations --check --noinput
just manage check
just pytest
```

Seeds must be proven idempotent (run twice).

## Locked decisions

| Area | Decision |
|---|---|
| Detail pages | `on_delete: "page"`; unresolvable source ⇒ 404; non-navigable `ModelDetailTemplate` for private records. |
| Peer profiles | `PeerIndexPage` admin-created; peer pages not under `/u/`. |
| Tag/user-profile visibility | Unchanged (inactive tag 404s incl. moderators; profile = active + visibility + blocks). |
| Search | Single project-contributed search block; merge meetings + peers + pages; index `StandardPage`; admin-authored only. |
| Feed scoping | `booking` seeker-scoped; add `host_booking`; page-aware querysets; `?page=` across AJAX. |
| Two-party access | Detail pages **and** feeds; viewer+page+status+date; participant-only; moderators allowed. |
| Date filters | Both `created_at` and session time. |
| Join windowing | `IntegrationSettings.joining_lead_minutes`; audience rules; server-enforced endpoint. |
| Join links | Transient (not persisted): Whereby cached property (`GET /meetings/{id}?fields=[hostRoomUrl]`); Daily private rooms + tokens. |
| Attendance | `host_attended`/`viewer_attended` from provider webhooks (idempotent). |
| Analytics | New `analytics` app; ledger-first; fee from `charge.application_fee_amount`; currency per-currency **and** converted. |
| Secrets | Fernet-encrypted DB fields; KEK = `DJANGO_SECRET_KEY`; all integration secrets encrypted. |
| Charts | `wagtailcharts` (Wagtail 8 compatible) with DaisyUI-theme-bridged colours + custom colours; server-computed data. |
| Consent | Code/persistence only; admins author the policy page and banner UX; no seeded legal text. |
| Developer docs | Authored prose under `docs/platform/`. |
| Review state | `ReviewStatus` (`PENDING_APPROVAL`/`PUBLISHED`/`HIDDEN`); `is_published` retired; moderator unpublish = peer hide = `HIDDEN`. |
| Review policy | `PeerProfile.reviews_require_approval` default `False`; peer toggles default public. |
| Help content | Code-owned; container start runs `seed_help_guide --force` (admin edits to seeded rows are overwritten on deploy). |

---

## Phase 0 — Correctness & security remediation (blocking)

Fix before feature work. Every item: failing test → fix → green; no behaviour
regression. Order within a group is the recommended execution order.

### 0.1 Commerce & payments (critical)

Ordered units; each is test-first (failing test → fix → green) with handovers.

#### Unit 1 — Per-request line items + Stripe-calculated amounts (Option A)

**Status: complete — green.** (ruff clean; scoped pytest + gates passed.)

**Goal.** Each `MeetingRequest`/`Booking` records the Stripe-calculated amount for
that specific item, never the combined Checkout Session total. Fixes "booking
never marks its child requests paid" and "multi-booking marks only the first".

**Confirmed decisions.**
- **Option A** — one line item per `MeetingRequest`; session-less (group)
  `Booking`s remain one line item each.
- Mapping via ordered `metadata["line_item_refs"]` (`"request:<pk>"` /
  `"booking:<pk>"`), built in lockstep with `line_items`.
- Mixed-currency peer cart ⇒ raise a clear `ValueError` (real fix = 0.1 M4
  grouping by `(peer, currency)`).
- `price_paid` = actual Stripe line-item `amount_total` (minor → major; includes
  tax/discount/adaptive pricing), never locally recomputed.

**Steps**
1. [x] `meetings/models/booking.py`
   - `_line_item` uses each item's own `meeting` for `currency`/`name` (not
     `peer_bookings[0].meeting`).
   - `_peer_session_kwargs`: one line item per `MeetingRequest` (amount
     `meeting.price_for(requested_duration_minutes)` else `meeting.price`; raise on
     `None`/`<=0`) and one per session-less `Booking`
     (`total_amount or compute_total()`); build `line_item_refs` in lockstep;
     store `metadata["line_item_refs"]` (keep `booking_ids`); sum for
     `build_charge_plan`; set each `Booking.total_amount` to its local item sum.
   - Raise `ValueError` when a peer group mixes currencies.
2. [x] `meetings/signals.py` — on `checkout.session.completed`, retrieve line
   items once (connected-account key, paginated) and map by index to
   `line_item_refs`:
   - `request:<pk>` → `price_paid = amount_total/100`, PI/session id,
     `receipt_url`; mark `PAID` only `if can_proceed`.
   - `booking:<pk>` → `total_amount = amount_total/100`; mark `PAID` only
     `if can_proceed`.
   - Idempotent; on retrieval failure log with context and leave unpaid (no silent
     fallback; Stripe retry/reconciliation completes).
   - Subsumes item 2 (all records in the session marked); item 3 (multi-peer
     redirect) stays out of scope.
3. [x] `meetings/tests/test_payments.py`
   - Two requests + a second booking in one session → per-request `price_paid`
     equals its own line-item amount; booking totals equal their sums, never the
     session total.
   - Session-less group booking → booking line item applied.
   - Replay idempotent. Patch `stripe.checkout.Session.retrieve`/
     `list_line_items`, `StripeSession.sync_from_stripe_data`, `receipt_url_for`.

**Acceptance.** Per-item amounts are exact and Stripe-calculated; replay-safe; no
migration and `makemigrations --check` clean.

```
HANDOVER
Purpose:   Confirm the new test fails before the fix.
Command:   just pytest neuromancers_network/meetings/tests/test_payments.py -k PerItemStripeAmounts -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env (DATABASE_URL)
Expected:  1 failed (pre-fix)
Blocked on: I implement; you re-run.
```
```
HANDOVER
Purpose:   Gates after the fix.
Command:   just manage makemigrations --check --noinput && just manage check && just pytest neuromancers_network/meetings/tests/test_payments.py -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  no changes detected; check clean; tests pass
Blocked on: I address failures, then pause for review.
```

#### Unit 2 — Multi-peer cart restriction

**Status: complete — green.** (ruff clean; `TestMultiPeerCart` passed.)

**Goal.** A cart spanning multiple care providers must not silently create
unreachable sessions; paying is per provider (Stripe direct charges require one
account per Checkout Session).

**Decision.** Restrict a cart to one peer and surface a clear user-facing message
when mixed (rather than serving sequential session URLs).

**Steps**
1. [x] `meetings/models/booking.py` — `create_checkout_session_for_bookings`
   raises `ValueError` when the bookings span more than one `peer_id` (defence in
   depth for non-action callers).
2. [x] `meetings/actions.py` — `bookings_checkout_many` pre-checks the selected
   bookings' peer ids; on more than one, `messages.error(...)` and
   `redirect_back(request)` (never a 500). Keep the empty-selection guard.
3. [x] `meetings/tests/test_payments.py` — mixed-peer selection redirects with an
   error and creates no Stripe session; the service raises for a mixed-peer list;
   single-peer checkout is unchanged.

**Acceptance.** No dangling sessions; mixed carts explain themselves; single-peer
checkout unchanged.

```
HANDOVER
Purpose:   Verify Unit 2.
Command:   just pytest neuromancers_network/meetings/tests/test_payments.py -k MultiPeerCart -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  pass
Blocked on: I address failures.
```

#### Unit 3 — Pricing correctness

**Status: complete — green.** (ruff clean; `TestComputeTotal` + `TestPricing` passed.)

**Goal.** A missing/unresolvable price must never silently fall back to the base
price or £0. Applies to duration-tier pricing, 1:1 checkout, and booking totals.

**Steps**
1. [x] `meetings/models/meeting.py` — `price_for`: for
   `pricing_type == DURATION_TIERS`, return `None` when no tier/option exists
   (no `self.price` fallback); keep the fallback for fixed/per-hour/sliding.
2. [x] `meetings/models/request.py` — `MeetingRequest.create_checkout_session`
   uses `price_for(requested_duration_minutes)` without the base-price fallback;
   raise when the amount is `None`/`<=0`.
3. [x] `meetings/models/booking.py` — `compute_total` reuses `_session_amount`
   and raises when a session price is unknown; for session-less bookings require
   a positive `meeting.price` (no `or Decimal("0")`).
4. [x] `meetings/tests/test_payments.py` — duration-tier with no tier →
   `price_for` is `None` and `compute_total` raises; fixed pricing still falls
   back to `meeting.price`; session-less booking with no price raises.

**Acceptance.** No silent £0/wrong-price charges; checkout and totals raise
`ValueError` for unresolvable prices.

```
HANDOVER
Purpose:   Verify Unit 3.
Command:   just pytest neuromancers_network/meetings/tests/test_payments.py::TestComputeTotal neuromancers_network/meetings/tests/test_payments.py::TestPricing -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  pass
Blocked on: I address failures, mark Unit 3 complete, and proceed.
```

#### Unit 4 — Refund correctness

**Status: complete — green.** (ruff clean; `TestRefundFlow` passed.)

**Goal.** Refund caps use the actual paid amount, and concurrent/duplicate refund
attempts cannot issue two Stripe refunds.

**Steps**
1. [x] `meetings/models/refund.py` — partial-refund cap uses
   `meeting_request.price_paid` + `_to_minor_units` (no advertised-price
   fallback); raise when no recorded payment.
2. [x] `meetings/models/refund.py` — `request_refund` serialises with
   `select_for_update`; `issue_stripe_refund` sends a stable Stripe
   `idempotency_key` (`refund:<meeting_request_id>[:<amount_minor>]`).
   `MeetingRequest.request_refund` persists `reason` before processing and no
   longer performs a redundant stale `save()`.
3. [x] `meetings/tests/test_payments.py` — partial refund without recorded
   payment raises; the Stripe call carries the idempotency key; a second request
   does not re-issue a refund.

**Acceptance.** No refund can exceed the recorded payment; duplicate requests are
idempotent at Stripe and locally.

```
HANDOVER
Purpose:   Verify Unit 4.
Command:   just pytest neuromancers_network/meetings/tests/test_payments.py::TestRefundFlow -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  pass
Blocked on: I proceed to the next remaining 0.1 unit.
```

#### Unit 5 — Commerce hardening (remaining 0.1)

**Status: complete — green.** (ruff clean; scoped tests + gates passed; tests
trimmed to behaviour-only, with pure helpers covered by no-DB tests.)

**Goal.** Adaptive pricing on 1:1, conditional `adaptive_pricing`, per-currency
grouping, retire the broken SEPARATE mode, routable checkout return pages,
half-up fee rounding; close the Unit 1 test gaps.

**Steps**
1. [x] 1:1 checkout sends `adaptive_pricing` when the exchange-rate source is
   Stripe (`meetings/models/request.py`; shared `charges.adaptive_pricing`).
2. [x] `adaptive_pricing` is only included in Checkout kwargs when enabled
   (`meetings/models/booking.py`).
3. [x] Carts are grouped by `(peer, currency)`; the service and action reject
   mixed peer/currency with clear errors/messages.
4. [x] `SEPARATE` removed from `StripeSettings.ChargeType`; migration
   `core/0011` maps `separate` → `direct`; charge/refund helpers use
   direct/destination only.
5. [x] Added `/pay/success/` + `/pay/cancelled/` views, templates and routes.
6. [x] Application fee uses `Decimal` half-up rounding.
7. [x] Closed Unit 1 test gaps: multiple bookings in one session; replay
   idempotency; conditional adaptive-pricing key.

**Acceptance.** A cart charges one peer/currency; 1:1 and booking checkouts send
adaptive pricing only when configured; the retired mode cannot be selected; post-
payment redirects resolve; fee rounding is half-up.

```
HANDOVER
Purpose:   Verify Unit 5 (and the hand-written migration).
Command:   just manage makemigrations --check --noinput && just manage check
           just pytest neuromancers_network/meetings/tests/test_payments.py::TestPerItemStripeAmounts neuromancers_network/meetings/tests/test_payments.py::TestCreateRequestCheckoutSession neuromancers_network/meetings/tests/test_payments.py::TestMultiPeerCart neuromancers_network/meetings/tests/test_payment_logic.py -q
           just pytest neuromancers_network/payments/tests/test_charges.py neuromancers_network/inbox/tests/test_signals.py -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  no changes detected; check clean; tests pass
Blocked on: I close 0.1 and proceed to 0.2.
```
(If `makemigrations --check` reports drift, run `just manage makemigrations core`
and paste the diff for review; apply with `just manage migrate`.)

**0.1 status:** complete once Unit 5 is green (Units 1–5).

### 0.2 Meetings lifecycle & scheduled tasks

Ordered units; each is test-first (failing test → fix → green) with handovers.

#### Unit 1 — Recurring series generation

**Status: complete — green.** (`test_recurrence.py` passed; migration `meetings/0008`.)

**Goal.** Generate the next occurrence per recurring series exactly once,
without advancing the source occurrence or violating title uniqueness.

**Steps**
1. [x] `meetings/tasks.py` — rewrite `generate_recurring_group_meetings`: series
   keyed by `(recurrence_rule, peer)`, `status=PUBLISHED` only,
   `get_or_create` on `(rule, peer, scheduled_at)`, copy M2M relations, no
   `advance_meeting`, and skip past/too-soon slots via
   `next_publishable_slot` (lead-time aware).
2. [x] `meetings/models/recurrence.py` — remove the now-unused
   `advance_meeting`.
3. [x] `meetings/models/meeting.py` — constraints: keep published-title
   uniqueness for non-recurring meetings; add a unique
   `(recurrence_rule, peer, scheduled_at)` slot constraint for series (allows
   occurrences to share a title).
4. [x] `meetings/tests/test_recurrence.py` — generates one future occurrence;
   idempotent; ignores drafts; respects `max_occurrences`/`end_date`.

**Acceptance.** One occurrence per slot; replays are no-ops; drafts/archived are
ignored; title constraint no longer crashes recurring generation.

```
HANDOVER
Purpose:   Generate + apply the constraint migration, then verify Unit 1.
Command:   just manage makemigrations meetings
           just manage migrate
           just pytest neuromancers_network/meetings/tests/test_recurrence.py -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  migration created + applied; tests pass
Blocked on: I review the migration, mark Unit 1 complete, and proceed.
```

#### Unit 2 — Session completion

**Status: complete — green.** (`test_tasks.py` passed; migration `meetings/0009`.)

**Goal.** Complete paid sessions after their scheduled end, for 1:1 and group
meetings, on a beat schedule.

**Steps**
1. [x] `meetings/tasks.py` — `mark_completed_sessions` uses the request's
   start/duration when set, else the meeting's scheduled start/duration; only
   completes after `start + duration`; logs paid rows missing schedule data.
2. [x] `meetings/migrations/0009` — schedule the task every 5 minutes via
   `django_celery_beat`, with a reverse that deletes it.
3. [x] `meetings/tests/test_tasks.py` — 1:1 complete after end; in-progress stays
   paid; group completes from the meeting schedule; unpaid and schedule-less rows
   untouched.

**Acceptance.** Completion happens after the session ends for both meeting types;
the task is scheduled; replays are idempotent.

```
HANDOVER
Purpose:   Verify Unit 2.
Command:   just manage migrate
           just pytest neuromancers_network/meetings/tests/test_tasks.py -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  migration applied; tests pass
Blocked on: I mark Unit 2 complete and proceed.
```

#### Unit 3 — Group capacity

**Status: complete — green.** (`TestGroupCapacity` passed.)

**Goal.** Enforce `max_participants` for group meetings against active bookings,
and count the right records in `is_fully_booked`/`available_spots`.

**Steps**
1. [x] `meetings/models/meeting.py` — capacity counts **pending/paid bookings**
   (not `MeetingRequest`s); cancelled/refunded bookings free a place.
2. [x] `meetings/services.py` — `create_booking` locks the meeting
   (`select_for_update`) and rejects when full.
3. [x] `meetings/tests/test_booking.py` — full group rejects; cancelled booking
   frees a spot; `is_fully_booked`/`available_spots` reflect bookings; 1:1 has no
   limit.

**Acceptance.** Group meetings never exceed capacity under concurrency;
cancelled/refunded bookings do not occupy places.

```
HANDOVER
Purpose:   Verify Unit 3.
Command:   just pytest neuromancers_network/meetings/tests/test_booking.py::TestGroupCapacity -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  pass
Blocked on: I mark Unit 3 complete and proceed.
```

#### Unit 4 — Meeting deletion

**Status: complete — green.** (`TestMeetingDeletion` passed.)

**Goal.** Deleting a meeting refunds/cancels its active sessions and notifies the
seekers before the cascade removes the rows.

**Steps**
1. [x] `meetings/services.py` — shared `_cancel_and_refund_requests`; add
   `cancel_and_refund_for_meeting`; `delete_meeting` cancels/refunds then deletes;
   `delete_all` does the same for a peer's meetings.
2. [x] `meetings/actions.py` — `meetings_delete` uses the service
   (`meetings_delete_all` already uses `delete_all`).
3. [x] `meetings/tests/test_meetings.py` — deletion cancels and emits
   `booking_cancelled`; auto-approved refunds emit `refund_refunded`; bulk delete
   cancels active requests.

**Acceptance.** No paid session is silently dropped on deletion; cancellation
notifications are emitted before the rows vanish.

```
HANDOVER
Purpose:   Verify Unit 4.
Command:   just pytest neuromancers_network/meetings/tests/test_meetings.py::TestMeetingDeletion -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  pass
Blocked on: I mark Unit 4 complete and proceed.
```

#### Unit 5 — Editing near the start time

**Status: complete — green.** (`TestMeetingSchedulingWindow` passed.)

**Goal.** Editing a published group meeting inside the 30-minute window must work;
the future-start rule applies only when the schedule changes or the meeting is
published.

**Steps**
1. [x] `meetings/models/meeting.py` — track the loaded schedule/status
   (`__init__`, `save`, `refresh_from_db`); `clean()` enforces the lead time only
   when the schedule changed or the status is moving to published.
2. [x] `meetings/tests/test_meetings.py` — editing inside the window succeeds;
   moving the schedule into the window is rejected; publishing inside the window
   is rejected.

**Acceptance.** Unrelated edits near the start time save; unsafe schedule changes
and publishes still fail.

```
HANDOVER
Purpose:   Verify Unit 5.
Command:   just pytest neuromancers_network/meetings/tests/test_meetings.py::TestMeetingSchedulingWindow -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  pass
Blocked on: I mark Unit 5 complete and proceed.
```

#### Unit 6 — Inbox reminders

**Status: complete — green.** (`test_tasks.py` passed; migration `inbox/0006`.)

**Goal.** Payment, session and upcoming-meeting reminders run on a schedule,
cover group bookings, and only fire for sessions a member can still attend.

**Steps**
1. [x] `inbox/tasks.py` — payment reminders use the status enum; session
   reminders use the request start, else the meeting schedule, and filter to
   approved/paid; upcoming-meeting recipients include active booking seekers
   (group attendees) plus request seekers, deduped.
2. [x] `inbox/migrations/0006` — schedule the three tasks every 5 minutes via
   `django_celery_beat`, with a reverse.
3. [x] `inbox/tests/test_tasks.py` — group session day reminder; inactive
   sessions skipped; group booking seeker receives `meeting_upcoming`; payment
   reminders dedupe.

**Acceptance.** Reminders run, include group attendees, and never remind
cancelled sessions.

```
HANDOVER
Purpose:   Verify Unit 6.
Command:   just manage migrate
           just pytest neuromancers_network/inbox/tests/test_tasks.py -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  migration applied; tests pass
Blocked on: I mark Unit 6 complete and proceed.
```

#### Unit 7 — Calendar events

**Status: complete — green.** (`test_calendar.py` passed.)

**Goal.** Only show calendar events for sessions a member can still attend and
for published group meetings; remove them when the source leaves those states.

**Steps**
1. [x] `peers/calendar.py` — request events materialise only for
   `APPROVED`/`PAID`; group-meeting events only for `PUBLISHED`; the existing
   remove-then-create keeps cancellations/archives clean.
2. [x] `peers/tests/test_calendar.py` — active request event; unapproved has
   none; cancellation removes; draft has none; published creates a public event;
   archive removes.

**Acceptance.** No events for unapproved/cancelled sessions or non-published
meetings.

```
HANDOVER
Purpose:   Verify Unit 7.
Command:   just pytest neuromancers_network/peers/tests/test_calendar.py -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  pass
Blocked on: I mark Unit 7 complete and proceed.
```

#### Unit 8 — ICS feed filtering

**Status: complete — green.** (`test_calendar_feed.py` + `TestBuildIcs` passed.)

**Goal.** The read-only ICS feed contains only sessions a member can still
attend, for published meetings.

**Steps**
1. [x] `core/views/calendar.py` — feed includes only pending/paid bookings for
   published meetings.
2. [x] `core/ical.py` — `_session_window` skips sessions that are not
   approved/paid.
3. [x] Tests — feed includes an active booking; excludes cancelled bookings and
   archived meetings; `build_ics` excludes cancelled sessions.

**Acceptance.** Cancelled/refunded bookings, inactive sessions and non-published
meetings are absent from the feed.

```
HANDOVER
Purpose:   Verify Unit 8.
Command:   just pytest neuromancers_network/core/tests/test_calendar_feed.py neuromancers_network/core/tests/test_exports.py::TestBuildIcs -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  pass
Blocked on: I mark Unit 8 complete and proceed to 0.3.
```

#### Unit 9 — Low-severity cleanup

**Status: complete — green.** (`TestRefundFlow` + `TestMeetingArchive` passed.)

**Goal.** Close the remaining small correctness gaps in the meetings domain.

**Steps**
1. [x] `meetings/models/refund.py` — add a `REJECTED → PENDING` `reopen`
   transition; `request_refund` reopens a rejected request and clears the peer
   response, allowing a new request.
2. [x] `meetings/models/meeting.py` — add an `ARCHIVED → DRAFT` `restore`
   transition so archived meetings are not a dead end.
3. [x] `meetings/models/meeting.py` + `request.py` — `populate_meeting_link`
   includes `updated_at` in `update_fields`.
4. [x] `meetings/models/meeting.py` — the lead-time error message uses
   `GROUP_MINIMUM_START_AHEAD_MINUTES` instead of a hardcoded 30.
5. [x] Tests — rejected refund can be re-raised; archived meeting can be
   restored.

**Acceptance.** Rejected refunds are re-raisable, archived meetings can be
restored, link writes bump `updated_at`, and the error text follows the
constant.

```
HANDOVER
Purpose:   Verify Unit 9.
Command:   just pytest neuromancers_network/meetings/tests/test_payments.py::TestRefundFlow neuromancers_network/meetings/tests/test_meetings.py::TestMeetingArchive -q
Cwd:       /Users/giraffe/neuromancers_network
Env:       project .env
Expected:  pass
Blocked on: I mark 0.2 complete and proceed to 0.3.
```

### 0.3 Accounts, identity & privacy
- [ ] **Reactivate doesn't cancel pending deletion ⇒ active users purged** — `users/services.py:139-166`, `moderation/services.py:127-145,245-256`. Cancel on reactivate; guard `is_active` in purge.
- [ ] **KYC ignores outstanding requirements (dict vs `getattr`)** — `payments/models/profile.py:111-136`. Read dict keys; normalise.
- [ ] **API PATCH bypasses username cooldown/blocklist/audit/uniqueness** — `users/api/views.py:38-53`. Route through `AccountForm`/validators.
- [ ] **Purge doesn't cancel Stripe subscription (billing after deletion)** — `moderation/services.py:148-159,209-228`. Cancel subscription on purge.
- [ ] **Anonymisation residual PII/privilege** — `moderation/services.py:162-206`. Scrub payment customer, `deactivation_reason`, staff flags; include `updated_at`; idempotent.
- [ ] **`purge_due_accounts` no error isolation/transaction** — `moderation/services.py:245-256`.
- [ ] **Signup quarantine emits `account_created`/email before deactivation** — `users/forms.py:51-79`. Set inactive before save/emission.
- [ ] Low: `active_session_keys` unbounded; `DeletedIdentity` never swept.

### 0.4 Integrations (Stripe & providers) hardening
- [ ] **Stripe disconnect deletes account possibly billing/with balance** — `payments/services.py:133-155`, `peers/actions.py:108-120`. Cancel subscription; guard balance; clean error.
- [ ] **`subscription_enabled` + provider agreement not enforced on subscribe** — `peers/actions.py:59-67`. Enforce; dead toggle.
- [ ] **Approved peer application can't be rejected via status** — `peers/models/application.py:45-52`. Derive status from transitions.
- [ ] **Remote calls: no idempotency/timeout/transaction** — `payments/services.py:51-118`, `users/avatar.py:30-40`. Idempotency keys, timeouts, don't hold transactions open.
- [ ] **`peer_connect_stripe` trusts request refresh/return URLs** — `peers/actions.py:49-56`. Use configured URLs / allowlist.
- [ ] **Pause/resume state webhook-only; bogus event names** — `peers/services.py:205-250`, `peers/signals.py:25-31`. Set local state on action; fix event list.
- [ ] **Subscription lapse not enforced on `past_due`/`unpaid`** — `peers/signals.py:78-113`.
- [ ] **Unbounded recurrence expansion loop (DoS)** — `peers/services.py:151-190`, `peers/calendar.py:57-78`. Clamp start; iterate lazily.
- [ ] **Dead settings** (`subscription_enabled`, `connect_country`, `onboarding_*`, `client_id`, `SubscriptionInterval`) — wire or remove.
- [ ] Low: stale in-memory `webhook_secret` (`payments/services.py:300-302`); `stripe_connect_account` `DoesNotExist` → 500 (`payments/services.py:88-91`); `default_terms_updated_at` `update_fields` mismatch (`peers/models/profile.py:108-117`).

### 0.5 Admin/feeds correctness
- [ ] **Email bans case-sensitive (bypass)** — `moderation/banning.py:26-30`. `__iexact` + normalise on save.
- [ ] **`settings.*` action fallback reads wrong kwarg ⇒ 404** — `users/settings.py:195-202`. Use `kwargs["key"]`.
- [ ] **`_allowed_page_types` raises `LookupError` ⇒ 500** — `core/selectors.py:13-21`. `try/except` + log.
- [ ] **Notification idempotency has no DB constraint** — `inbox/events.py:100-108`, `inbox/models/notification.py:28-33`. `UniqueConstraint(["recipient","event_ref"])`.
- [ ] **`pre_state_store` process-global leak/thread-shared** — `inbox/signals.py:43-72`. `WeakKeyDictionary`; guaranteed cleanup.
- [ ] **Export sweep unbounded retries** — `moderation/export.py:278-290`, `moderation/tasks.py:24-27`. Attempt counter → terminal FAILED.
- [ ] **Bulk ticket reject emits `report_resolved`** — `moderation/wagtail_hooks.py:155-188`. Distinct event/status.
- [ ] **`SupportFormPage` ignores model mapping / never sets `subject_user`** — `moderation/forms_pages.py:30-46`.
- [ ] Low: export download 302 vs 403 (`moderation/views.py:31-36`); dead calendar link helpers (`core/ical.py:50-75`); localization middleware default (`core/middleware.py:30-34`); `tag_choices` ignores inactive group (`taxonomy/selectors.py:45-50`); string-literals-vs-enums (`meetings/tasks.py:21,24`, `inbox/tasks.py:35`); dead/duplicated code (`request.py:247-348`, `_MEETING_FIELDS`, `MeetingPriceTier.is_default`, selector aliasing).

---

## Phase A — Data access patterns

Goal: every detail page resolves its own model instance from URL path parameters;
search is fully admin-authored; two-party records (requests/bookings/refunds) are
scoped and reachable per the UX flows; meeting join is time-boxed and
provider-aware. All bugs below were found by static review (`REASONED`) — each is
fixed **test-first** (failing test → fix → green), no regressions.

Dependencies: A3 depends on Phase 0.1/0.2; A4 depends on B0 (secret storage).

### A1 — Detail-page instance resolution

Steps (in order):
1. [ ] Set `"on_delete": "page"` for `meeting`, `peer_profile`, `review`,
   `user_profile` (`config/settings/base.py:1225,1237,1249,1261`); `tag` already
   `"page"`. Deleting a source deletes its page.
2. [ ] **Bug — orphan detail pages are served (404 bypass).**
   `hide_inaccessible_detail_pages` returns `None` when `source is None`
   (`core/wagtail_hooks.py:151-154`), so `unlink`ed/live orphans serve with 200.
   Detect a detail page structurally (`isinstance(specific, ModelDetailPage)`)
   and render 404 when `source_object_id` is set but `source is None`.
3. [ ] **Bug — `_SOURCE_PARAM` is a no-op / misleading.** Set the context models'
   `lookup_field` to the published param names (`meeting` → `meeting_pk`,
   `peer_profile` → `peer_pk`, `review` → `review_pk`) so binding actually uses
   them; keep `_SOURCE_PARAM` as the single source of truth for those names
   (`core/models/pages.py:17-45`, `config/settings/base.py:653,663,699`).
4. [ ] **Bug — an owner's unpublished meeting renders an empty context.**
   Binding uses `published_meetings` (`config/settings/base.py:654`) while the
   visibility guard lets the owner through, so `{{ meeting }}` is `None` for the
   owner. Provide an owner-aware queryset for detail-page binding.
5. [ ] **Bug — `request.daisie_path_params` mutation accumulates** across
   `get_context` calls (`core/models/pages.py:56-60`). Build a fresh copy; do not
   leak params across pages/requests.
6. [ ] **Bug — `get_absolute_url` fallbacks can 404** (`/meetings/<pk>/`,
   `/peers/<username>/`, `/reviews/<pk>/`, `/u/<username>/`) when the bridge page
   is absent. Guarantee pages exist (bridge) and make fallbacks safe/covered by
   tests.
7. [ ] Add `index.SearchField("bio")` to `UserProfile.search_fields`
   (`users/models/profile.py:122-129`).
8. [ ] Tests: per-type context var populated; unrelated URL-sourced models pruned;
   orphan/unpublished/missing → 404; deleting source deletes page; params not
   leaked.

Acceptance: each detail type resolves its instance; no cross-binding; source-less
⇒ 404; `makemigrations --check` clean.

### A2 — Unified, admin-authored search

Steps:
1. [ ] Index `StandardPage` (title/description/body) and contribute a search block
   (via `register_content_block`) that merges meetings + peer profiles + pages,
   with deterministic ordering and pagination.
2. [ ] **Bug — site search returns nothing / dead code.**
   `SearchPage.get_context` builds `search_results` (`core/models/pages.py:136-174`)
   but `core/templates/core/search_page.html` only renders `page.body`, and the
   seeded page body is empty, so `/search/?query=` is blank. Remove the dead
   `get_context` and render results through the block (or a real template).
3. [ ] **Bug — search results cause N+1.** `results = [*meetings, *peers]`
   (`pages.py:171`) then `get_absolute_url` per row. Batch the page lookups / use
   `select_related`; cap results.
4. [ ] **Bug — reserved-slug validation is dead, auto-slug bypass.**
   `ReservedSlugPage.clean_slug` (`core/models/pages.py:81-89`) is never called by
   Wagtail; enforcement relies on POST-slug hooks (`core/utils.py:39-62`) which
   pass when the slug is blank. Implement `clean()` (or slug-field validators) and
   slugify the title in the hooks when the submitted slug is blank.
5. [ ] **Bug — `_allowed_page_types` raises `LookupError` ⇒ 500.** `apps.get_model`
   raises for a bad path (`core/selectors.py:13-21`). Wrap in `try/except
   LookupError` and log/skip.
6. [ ] Tests: search renders merged results; visibility respected; reserved slug
   rejected for auto-generated slugs; bad content-type config does not 500.

Acceptance: `SearchPage` issues no model queries itself; results respect
visibility; ordering deterministic.

### A3 — Two-party scoping (requests · bookings · refunds)

Steps:
1. [ ] **Bug — booking/refund detail pages are effectively public.**
   `source_owner(Booking|RefundRequest)` is `None` and there is no `publish_field`,
   so `viewer_can_view_source` returns `True` (`moderation/visibility.py:82-99,
   159-181`). Add `source_participant_ids` (booking ⇒ seeker + `meeting.peer`;
   refund ⇒ `meeting_request.support_seeker` + `meeting_request.meeting.peer`) and
   short-circuit: moderator ⇒ True; participant ⇒ True; else deny.
2. [ ] Add non-navigable `BookingDetailTemplate`/`RefundRequestDetailTemplate`
   (`ModelDetailTemplate` subclasses under `HomePage`) and
   `BookingDetailPage`/`RefundRequestDetailPage` (context via
   `booking_for_viewer`/`refund_for_viewer`).
3. [ ] Add `publish_field`/`lookup_field`/`title_source`/`slug_source` entries and
   `on_delete: "page"` for `booking`/`refund_request`.
4. [ ] Selectors (`meetings/selectors.py`): `viewable_bookings`,
   `viewable_refunds`, `booking_for_viewer`, `refund_for_viewer`,
   `bookings_for_context`, `refunds_for_context`, `meeting_requests_for_context`,
   `user_requests`, `user_refunds`, `host_bookings`; viewer+page scoped; status +
   date (`created_at` **and** session time) filters.
5. [ ] **Bug — `refund_request` context model has no queryset** ⇒ `.all()`
   fallback (`config/settings/base.py:756-760`); add a scoped queryset +
   `select_related`.
6. [ ] **Bug — model feeds lose page scope on AJAX.** `feed.html` emits the hidden
   `page` input only for page-tree feeds (`templates/wagtail_daisIE/blocks/data/
   feed.html:21`). Emit it whenever `host_page` is present; selectors honour
   `?page=`.
7. [ ] Depends on Phase 0.1 (payment propagation) / 0.2 (completion) for correct
   data.
8. [ ] Tests: the 12 UX flows return only in-scope rows; stranger ⇒ empty/404;
   replay-safe; no N+1.

Acceptance: all listed flows work; no cross-user leakage.

### A4 — Meeting join windowing + providers

Steps:
1. [ ] Add `IntegrationSettings.joining_lead_minutes` (additive migration).
2. [ ] **Bug — join has no time window.** `MeetingRequest.can_join`
   (`meetings/models/request.py:162-169`) checks status only. Add audience rules
   `is_joining_upcoming_meeting_as_host|guest` resolving the target (**Meeting**
   for group, **MeetingRequest** for 1:1 — current `_meeting` only resolves
   `Meeting`, `core/audience.py:72-78`), window `start − lead ≤ now ≤ end`.
3. [ ] Server-enforced join endpoint (re-checks role + window; the button is
   cosmetic).
4. [ ] Whereby host link as a cached property (`GET /meetings/{id}?fields=
   [hostRoomUrl]`); guest = stored `roomUrl`.
5. [ ] Daily: rooms `privacy: "private"`; extend the vendored client with
   `POST /meeting-tokens` (owner/non-owner, `nbf`/`exp`, `user_id`); links
   `room.url?t=<token>`.
6. [ ] **Bug — provider not captured per session** (only global setting +
   `provider_room_id`), so minutes-per-provider is impossible. Add a `provider`
   field at room creation (feeds B6).
7. [ ] Attendance webhooks (`host_attended`/`viewer_attended`) — depends on B0.
8. [ ] Tests: window for both roles; endpoint rejects out-of-window/non-
   participant; token/link mocked.

Acceptance: button visibility matches the window; endpoint enforced; provider
recorded.

### A5 — Admin guide (identity)
1. [ ] MeetingRequest-vs-Booking article (request to join vs confirmed purchase).
2. [ ] **Doc bug** — correct "Video providers: Whereby, GetPronto, Daily"
   (GetPronto is file upload, not video) (`core/help_seed.yaml:1086-1098`).
3. [ ] Provider overview (Whereby/Daily/GetPronto/Stripe).

Acceptance: `seed_help_guide` idempotent; articles render.

---

## Phase B — Analytics

Goal: admin-facing metrics (optionally user-facing), fed by idempotent ledgers,
rendered on an admin dashboard, a contributed chart block, and a read-only API.
Metric set: users, peers (+verified), meetings, meeting minutes (per provider),
GBV, platform fee revenue, subscription revenue, AOV, take rate, subscriptions,
requests/bookings by status + date, refunds (count/value/rate), failed payments,
reviews/rating, moderation. Scopes: platform (admin), peer, user. Buckets:
all-time / this month / last month / last 3 months (UTC calendar months).
Currency: per-currency **and** converted (checkout rate for `stripe`, else
`LocalizationSettings`). Ledger-first; no rollups. All bugs below are `REASONED` —
fix test-first, no regressions.

Dependencies: B0 precedes B1/B6; B1 depends on Phase 0.1/0.2; B4 depends on 0.1;
B5 depends on 0.2.

### B0 — Secure secret storage (prerequisite)

Goal: no integration secret is plaintext at rest.

Steps:
1. [ ] New `EncryptedCharField`/`EncryptedTextField` (Fernet key derived from
   `DJANGO_SECRET_KEY` via `hashlib.sha256` → urlsafe base64; fail fast if absent).
2. [ ] Convert `StripeSettings.secret_key`/`webhook_secret`/`client_id`,
   `EmailSettings.password`, `IntegrationSettings.*_api_key`, and the new
   Whereby/Daily webhook secrets (`core/models/settings.py:38-54,161,221-238`).
3. [ ] Masked admin widget with "leave blank to keep existing".
4. [ ] Forward-only data migration to encrypt existing rows; document rollback.
5. [ ] **Bug/risk — settings revisions may persist plaintext.** Spike first:
   exclude secret fields from revisions (or serialise ciphertext); assert with a test.
6. [ ] **Risk — `DJANGO_SECRET_KEY` rotation** makes ciphertext unreadable; add a
   startup warning + runbook note.
7. [ ] **Bug (0.4) — stale in-memory secret**: `create_webhook_endpoint` updates
   `webhook_secret` via `.update()` but not the instance
   (`payments/services.py:300-302`); refresh after write.
8. [ ] Tests: round-trip, blank-keeps-existing, no plaintext in revisions, migration
   idempotent.

Acceptance: no plaintext secret at rest/in revisions/admin; `makemigrations --check` clean.

### B1 — Idempotent ledgers

Goal: replay-safe records; **marketplace revenue and subscription revenue tracked
in separate ledgers** (combined only for display, see B3).

Steps:
1. [ ] New `neuromancers_network/analytics/` app. Models:
   - `TransactionLedger` — **marketplace** money: kind (booking_payment, refund,
     application_fee, dispute), base/presentment currency + amounts,
     `exchange_rate`, `fee_amount`, `net_amount`, payer/payee, provider object id,
     `occurred_at`, unique `idempotency_key`.
   - `SubscriptionLedger` — **subscription** revenue: kind (subscription_payment,
     subscription_refund), invoice/subscription id, payer, currency/amounts,
     `occurred_at`, unique `idempotency_key`.
   - `SessionLedger` — `meeting_request` OneToOne, `provider`, `minutes`,
     peer/seeker, `occurred_at`.
   - `ActivityLedger` — event_type, object_type/id, `occurred_at`, unique.
2. [ ] Writers via `update_or_create` keyed on provider object id, wired to the
   existing `meetings/signals.py` receivers.
3. [ ] **Bug — refund value is never captured.** `handle_charge_refunded`
   (`meetings/signals.py:95-123`) ignores `refund_data["amount"]` and
   `RefundRequest` has no amount; record the refund amount in `TransactionLedger`.
4. [ ] **Subscription revenue (own ledger).** Add
   `invoice.payment_succeeded`/`invoice.paid` receivers (`peers/signals.py`) →
   `SubscriptionLedger`.
5. [ ] **Bug — disputes synced but not recorded** (`meetings/signals.py:125-135`);
   add `dispute` to `TransactionLedger`.
6. [ ] **Bug — fee not persisted** (computed at checkout, `payments/charges.py:
   37-38`); record `fee_amount` from `charge.application_fee_amount` (fallback to
   the configured percent).
7. [ ] **Dependency — 0.1 payment propagation and 0.2 completion** must be fixed or
   ledgers are empty/incorrect.
8. [ ] `sync_analytics_ledgers` idempotent backfill.
9. [ ] Tests: replay-safe; fixed-clock determinism.

Acceptance: replay-safe ledgers; `makemigrations --check` clean.

### B2 — Metric definitions

Goal: one pure, testable metric layer.

Steps:
1. [ ] Pure functions by scope (platform/peer/user) and period (UTC months);
   documented definitions (GBV, take rate, session minutes, active member/peer,
   repeat-booking rate, refund rate, published-review rate).
2. [ ] Currency: per-currency **and** converted.
3. [ ] **Bug — `convert_amount` cannot convert for `stripe` source** (returns
   unchanged, `core/currency.py:36-39`); use the B4-persisted checkout rate.
4. [ ] **Bug — conversion direction/keys ambiguous** (`rates.get(target)` ignores
   source, `core/currency.py:42-47`); define source→target semantics + validate.
5. [ ] **Bug — `convert_amount(None)` crashes** (`Decimal(str(None))`); guard
   `None`/empty.
6. [ ] **Bug — enum drift** (`meetings/tasks.py:21,24`, `inbox/tasks.py:35`); filter
   via `TextChoices`.
7. [ ] Define "active member/peer"; reuse `eligible_peer_q`, `exclude_hidden`,
   live/public.
8. [ ] Tests: deterministic outputs; conversion fallback; enum-correct filters.

Acceptance: deterministic metrics; conversion proven.

### B3 — Surfaces

Goal: admin, authored-page and API access to metrics.

Steps:
1. [ ] Staff-only admin analytics view + homepage panel (`register_admin_urls`/
   `construct_homepage_panels`; pattern `HelpGuideView`). Revenue shown split
   (marketplace vs subscription) with a **combined figure as a cached property**.
2. [ ] Contributed **metric chart block** (`register_content_block`), server data,
   wagtailcharts frontend, DaisyUI-theme-bridged colours (draftail CALLABLE
   pattern) + custom colours; audience-gated for user-facing use.
3. [ ] Read-only django-ninja `/api/analytics/` (staff platform scope; self-scope
   for members).
4. [ ] **Risk — `register_content_block` import order** (`wagtail_daisIE/blocks/
   content.py`); verify load order or extend daisIE's hook.
5. [ ] **Schema note** — block changes the page `body` StreamField → migration.
6. [ ] Tests: admin render; block renders metric/period/scope; API authz.

Acceptance: admin view, block, API work; no N+1 on series.

### B4 — Payment currency capture

Goal: every payment records base and presentment amounts + rate.

Steps:
1. [ ] **Bug — 1:1 checkout lacks adaptive pricing** (`meetings/models/request.py:
   270-320`).
2. [ ] **Bug — `adaptive_pricing=None` sent unconditionally**
   (`meetings/models/booking.py:176-185`).
3. [ ] **Bug — mixed currencies collapsed in a peer cart**
   (`meetings/models/booking.py:140-164`).
4. [ ] **Bug — `compute_total` charges £0 for a missing tier price**
   (`meetings/models/booking.py:103-115`).
5. [ ] **Bug — `price_for` silently falls back to base price**
   (`meetings/models/meeting.py:425-434`).
6. [ ] **Bug — `sync_payment_from_checkout` stores only presentment**
   (`meetings/models/request.py:333-345`); persist base GBP + presentment + rate.
7. [ ] `UNVERIFIED` — confirm the Stripe conversion-rate field (e.g. PaymentIntent
   `currency_conversion`); store when present, else `LocalizationSettings`.
8. [ ] Key/value widget for `LocalizationSettings.manual_exchange_rates` (none in
   `wagtail_daisIE.widgets`).
9. [ ] **Bug — application fee banker's rounding** (`payments/charges.py:37-38`).
10. [ ] Tests: base+presentment persisted; converted metrics use Stripe rate with
    fallback.

Acceptance: both currencies stored; conversion correct.

### B5 — Public exposure + peer controls

Goal: admins publish aggregates; peers control their own exposure (default
public) **and review publication**; peers may **hide (never delete)** reviews;
reviewers' reviews publish immediately unless the peer requires approval.

Steps:
1. [ ] Public aggregates on Meeting/Peer pages (rating, rating count, sessions
   count, published reviews), audience-gated and block-aware.
2. [ ] Peer preferences on `PeerProfile` (additive, defaults = public):
   `show_review_rating`, `show_rating_count`, `show_sessions_count`,
   `accepts_reviews` (all `True`), and `reviews_require_approval` (`False`).
3. [ ] **Review state model (single source of truth).** Introduce
   `ReviewStatus` (`PENDING_APPROVAL`, `PUBLISHED`, `HIDDEN`), indexed, and
   **retire `Review.is_published`**. Keep `is_live` as a derived property
   (`status == PUBLISHED`) so `moderation/visibility.py`
   `publish_field: "is_live"` is unchanged. Data migration maps existing rows to
   `PUBLISHED`; the `is_published` column drop is a **breaking migration** with a
   rollback note (reverse-map status → boolean).
4. [ ] Update callers: `published_reviews` → `status=PUBLISHED`
   (`meetings/selectors.py:37`); admin `ReviewViewSet` list/panels and the
   Publish/Unpublish bulk actions → set `status` (`Publish` → `PUBLISHED`,
   `Unpublish` → `HIDDEN`) (`meetings/wagtail_hooks.py:228-233,407-447`);
   `inbox/payloads.py:235`.
5. [ ] **Approval flow.** On creation (`ReviewFormPage`,
   `meetings/forms_pages.py:225-251`), set `status = PENDING_APPROVAL` when the
   peer's `reviews_require_approval` is `True`, else `PUBLISHED`.
6. [ ] **Peer actions.** Register `review.approve` / `review.hide` in
   `WAGTAIL_DAISIE_ACTIONS` (audience `peer`), authorized to the review's `peer`
   only, idempotent; expose a peer review list (pending/published/hidden) via the
   daisIE feed/dashboard pattern. **No delete action** for peers. Both moderator
   unpublish and peer hide set `HIDDEN` (audit log records the actor).
7. [ ] **Notifications — extend `NotificationEventType`** (`inbox/models/
   event_type.py`) with `review_pending_approval`, `review_published`,
   `review_hidden`; emit on the transitions (peer notified on pending; reviewer on
   approve/hide). Add bridge mappings/opt-outs.
8. [ ] **Bug — reviews auto-publish today** (`meetings/models/review.py:33`): fixed
   by steps 3–5; assert pending reviews never render publicly.
9. [ ] **Bug — counts must exclude cancelled/refunded and hidden parties**, and now
   also non-`PUBLISHED` reviews; apply active-status + `exclude_hidden`.
10. [ ] **Dependency — review creation unreachable until Phase 0.2** (only
    `MeetingRequestStatus.COMPLETED`, `meetings/forms_pages.py:238-242`;
    `mark_completed_sessions` unscheduled).
11. [ ] Tests: policy on → pending until approved; peer approve/hide transitions;
    peer cannot delete; owner/visitor view honours status + preferences; blocked/
    unpublished excluded; default-public behaviour.

Acceptance: peers control review publication (approve/hide, hide-only);
moderator unpublish and peer hide both `HIDDEN`; public surfaces show only
`PUBLISHED` reviews honouring preferences and blocks; default `False`
(auto-publish).

### B6 — Provider minutes

Goal: minutes per month per provider (Whereby / Daily), switchable.

Steps:
1. [ ] **Bug — `provider` not recorded per session**; add a `provider` field at
   room creation on `Meeting` and `MeetingRequest` (additive).
2. [ ] Inbound Whereby + Daily webhook endpoints (dashboard-configured; secrets via
   B0), signature-verified, idempotent; map `provider_room_id` → session; minutes
   by `provider`.
3. [ ] **Dependency — `daily` client lacks tokens/webhooks**; extend via
   `clientele` regen (handover) and set rooms `privacy: "private"`.
4. [ ] Admin view: switch minutes by provider.
5. [ ] Tests: mocked webhooks; replay idempotent; switch correct.

Acceptance: minutes-by-provider correct and switchable.

---

## Phase C — Scripts & cookie consent

Goal: admins can add scripts (head/body) and author a cookie policy + consent
banner; users can consent or decline; non-essential scripts load only after
consent. Code/persistence only — no seeded legal text; admins own the policy page
and banner UX. The cookie registry drives both the policy page and the banner
(single source of truth). Consent is **cookie-only**. CSP is **documented, not
enforced** in this phase. All bugs below are `REASONED` — fix test-first, no
regressions.

### C1 — Admin script injection
Steps:
1. [ ] Add a `ScriptsSetting` (Wagtail `BaseGenericSetting`) with head/body script
   entries (name, category, code, placement) + per-script audience gating; render
   via the unused `{% block extra_head %}` / `{% block extra_body %}`
   (`templates/base.html:32-33,50-51`).
2. [ ] Follow the `ArbitraryCSSMiddleware` / arbitrary-CSS pattern
   (`wagtail_daisIE/middleware.py`) for consistency (DRY): a settings model plus a
   small render path.
3. [ ] **Bug — no injection point today** (blocks unused): wire it and cover with a
   render test.
4. [ ] **Risk (documented) — no CSP** (no `django-csp`): admin scripts are
   unconstrained. Document CSP/nonce guidance for C4; gate editing on admin
   permission and audit changes.
5. [ ] **Risk (documented) — `X_FRAME_OPTIONS = "DENY"`**
   (`config/settings/base.py:309`) conflicts with third-party embeds; document
   per-script guidance.
6. [ ] Tests: head/body scripts render only when configured, permitted and
   consented; nothing else renders.

Acceptance: admins can add scripts; nothing renders that is not configured,
permitted and consented.

### C2 — Cookie registry + policy page
Steps:
1. [ ] Add `CookieCategory` (`necessary`/`analytics`/`marketing`) and `Cookie`
   snippets (name, provider, purpose, duration, category), admin-editable.
2. [ ] Policy page = an **admin-authored `StandardPage`** fed by the registry via a
   template tag/block; admins author the surrounding copy — no seeded legal text.
3. [ ] **Bug — undisclosed cookies.** Register the **language** cookie
   (`core/middleware.py:41`, set by `LocaleMiddleware`) and the **`daisie_theme`**
   cookie (`theme_persistence.js`, read in `wagtail_daisIE/pages.py:212`), plus
   session/CSRF as `necessary`.
4. [ ] **Cross-ref (0.5)** — `LocalizationMiddleware` default-language bug
   (`core/middleware.py:30-34`) must be fixed so the language cookie behaves
   deterministically.
5. [ ] Tests: registry renders on the policy page; categories drive the banner (no
   drift); session/CSRF marked necessary.

Acceptance: every cookie in use is registered and shown; the policy page is
admin-owned and registry-driven.

### C3 — Consent banner + persistence (cookie only)
Steps:
1. [ ] Admin-authored banner UX; persistence = **a single consent cookie**
   (categories + policy version + timestamp; JSON, signed/checked) — no
   server-side record.
2. [ ] **Bug — non-essential scripts render before consent.** Gate script
   rendering server-side on the consent cookie so tracking never ships until
   accepted; essential stays.
3. [ ] **Bug — no `Vary`.** Add `Vary: Cookie` to consent-dependent responses (or a
   small middleware) so caches don't serve mixed consent states.
4. [ ] Support change/withdraw (re-open banner) and policy **versioning** (re-ask
   after a policy change).
5. [ ] Accessibility + localization of the banner.
6. [ ] Tests: decline ⇒ no non-essential script; accept ⇒ scripts render; changing
   consent updates; version bump re-asks; `Vary: Cookie` present.

Acceptance: consent recorded (cookie) and honoured; declining suppresses
non-essential scripts; no cross-user cache bleed.

### C4 — CSP & security (documentation only)
Steps:
1. [ ] Document `Content-Security-Policy` requirements and nonce support for
   admin-injected scripts (`extra_head`/`extra_body`) and daisIE inline scripts
   (`{% daisie_htmx %}` etc.) — **no enforcement this phase**.
2. [ ] Document `frame-ancestors` vs `X_FRAME_OPTIONS` for embeds.
3. [ ] `UNVERIFIED (documentation)` — note which daisIE inline scripts would need
   nonces/hashes if CSP is enforced later.
4. [ ] No code/tests required; a docs deliverable only.

Acceptance: CSP interaction is documented; enforcement explicitly deferred.

---

Phase C bugs added: undisclosed cookies (language/theme/session/CSRF), missing
script-injection point, missing `Vary: Cookie`, non-consented script rendering,
language-middleware cross-ref. CSP and `X_FRAME_OPTIONS` recorded as documented
risks (not enforced).

## Phase D — Documentation

Goal: authored prose (admin + developer) covering **every feature**, how to use
it, and where it lives in code, including each provider. Docs are code: the help
seed must validate and stay idempotent; container start refreshes the admin guide.
English only. All bugs below are `REASONED` — fix test-first where testable, no
regressions.

Dependencies: D2's comparison tables need the help-seed `table` body type (A5);
D1's Stripe article assumes 0.4 wires `connect_country`/`client_id`/
`onboarding_*`/`subscription_enabled` (make that true in 0.4).

Note: Sphinx already uses `myst_parser` with `.md` in `source_suffix`
(`docs/conf.py:41-54`); `docs/platform/*.md` builds once added to a toctree. No
docs-build CI (manual check).

### D1 — Fix drift + refresh admin guides on deploy
Steps:
1. [ ] **Bug — Stripe article documents dead settings** (`core/help_seed.yaml:
   187-212`): keep it describing them as live and **wire them in 0.4**
   (`connect_country`, `client_id`, `onboarding_redirect_url`,
   `onboarding_refresh_url`, `subscription_enabled`).
2. [ ] **Bug — GetPronto mislabeled as a meeting/video provider**
   (`help_seed.yaml:239-262,1086-1098`); describe it as file upload.
3. [ ] **Bug — charge-type description** (`help_seed.yaml:187`): correct
   `Separate` semantics (or fix the code in 0.1).
4. [ ] **Bug — README boilerplate/command drift** (`README.md:18-22`): use
   `just manage …` conventions.
5. [ ] **Bug — `docs/index.rst` toctree** (`docs/index.rst:9-15`): add the platform
   tree.
6. [ ] **Bug — `docs/notifications.rst` event list** must match
   `NotificationEventType` (incl. B5 `review_*`).
7. [ ] **Bug — `docs/spec/daily.openapi.yaml`** omits meeting tokens; note/regen
   (A4/B6).
8. [ ] Verify `docs/infra/pricing.md` against the code; correct as needed.
9. [ ] **Admin guides are code-owned — refresh on deploy.** Change
   `compose/production/django/start` and `compose/local/django/start` to run
   `python /app/manage.py seed_help_guide --force` (currently no `--force`), so a
   deploy overwrites seeded help rows from `help_seed.yaml`. Document the tradeoff
   (admin edits to seeded rows are overwritten on deploy; other seeders — pages,
   account self-service — stay non-force).
10. [ ] Tests: help-seed validation covers all articles (slug length, category
    refs, body types).

Acceptance: no stale/dead-setting claims; toctrees complete; seed validates;
`--force` refresh runs at container start.

### D2 — Admin guide content
Steps:
1. [ ] Extend the help-seed loader with a `table` body type (A5) and render it in
   the reader (`core/help_seed.py:18`, `core/views/help.py`).
2. [ ] Add/refresh articles for: review approval + peer hide (B5), meeting join
   windowing (A4), analytics (B3), scripts & cookie consent (C), two-party records
   (A3), search (A2).
3. [ ] Add comparison tables: **Stripe charge types** (direct/destination/separate)
   and **Whereby vs Daily** (host/guest links, tokens, room lifetime, cost).
4. [ ] Keep seeding idempotent under the non-force path; `--force` is the
   deploy-refresh path (D1 step 9).

Acceptance: every feature has an admin article; both seed paths validated.

### D3 — Developer platform docs (`docs/platform/`)
Steps:
1. [ ] Create the `docs/platform/` `.md` tree and add it to a toctree (root or
   `docs/platform/index.md`).
2. [ ] Authored prose: architecture, data model, feature → code-location index,
   configuration/environment (incl. `DJANGO_SECRET_KEY` as the field-encryption
   KEK), daisIE usage, analytics ledgers, scripts/consent, and **each provider**
   (Whereby, Daily, GetPronto, Stripe).
3. [ ] Cross-link `docs/infra/*` runbooks rather than duplicating (DRY).
4. [ ] English only.

Acceptance: every feature and provider has a developer entry; no dead links.

### D4 — Validation & tooling
Steps:
1. [ ] Manual Sphinx build check with no broken toctrees (handover; **not** added
   to CI).
2. [ ] Keep `docs/platform` references consistent across roadmap/help.

Acceptance: docs build clean (manual); drift detectable.

---

Phase D bugs added: dead-setting Stripe article, GetPronto mislabel, charge-type
error, README drift, missing toctree, notifications event drift, Daily spec gap,
loader table gap, pricing-doc verification, and failure to refresh admin guides at
container start.

---

## Review gates

Sequence: **0.1 → 0.6 → A1 → A2 → A3 → A4 → A5 → B0 → B1 → B2 → B3 → B4 → B5 → B6 → C → D.**
Each unit: failing test → small reviewable diff → verification → `just pytest`
handover → **pause for review** → one commit. No unit starts before the previous
is reviewed.
