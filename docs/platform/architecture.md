# Architecture

## Stack

- **Django 6** with **Wagtail 8** for the admin, pages, snippets and search.
- **wagtail-daisIE 3.5** provides the design system, blocks, feeds, form pages,
  detail pages, actions, audiences and notification bridges.
- **PostgreSQL** for data; **Redis** for cache and Celery; **S3-compatible**
  storage for media and private exports.
- **Celery** (with `django_celery_beat`) for recurring tasks and webhook-adjacent
  work.
- Containers are built from `compose/` and deployed via Coolify (see
  [`../infra/deployment-pipeline.md`](../infra/deployment-pipeline.md)).

## Application layout

`LOCAL_APPS` in `config/settings/base.py` lists the project apps:

| App | Responsibility |
|---|---|
| `core` | Site pages/detail pages, settings models, search, consent/scripts, help, audit, uploads. |
| `users` | Custom user, profiles, identity controls, sessions, signup. |
| `peers` | Peer profiles/applications, subscriptions, availability, calendar. |
| `meetings` | Meetings, bookings, requests, reviews, refunds, join logic, selectors/actions. |
| `payments` | Stripe Connect, charges, webhook sync, secrets-aware helpers. |
| `taxonomy` | Tags/groups, languages, countries. |
| `inbox` | Event bus, notification materialisation, email bridges, reminders. |
| `moderation` | Bans, blocks, support tickets, exports, account deletion, visibility. |
| `analytics` | Ledgers, metrics, admin dashboard, API and chart block. |

Settings are split under `config/settings/` (`base.py`, `local.py`, `test.py`,
`production.py`). Environment-driven values are documented in
[Configuration](configuration.md).

## Request flow

1. Middleware (`config/settings/base.py`): security, sessions, locale, the
   project `LocalizationMiddleware`, `ConsentVaryMiddleware`, htmx/daIsIE
   middleware.
2. Wagtail serves pages; generated `ModelDetailPage` subclasses in
   `core/models/pages.py` resolve their own source and enforce visibility in
   `core/wagtail_hooks.py`.
3. Admin-authored data components use daisIE feeds/actions; action handlers live
   in each app's `actions.py` (registered in `WAGTAIL_DAISIE_ACTIONS`).
4. Domain writes go through models/services; side effects are emitted onto the
   inbox event bus and to daisIE email bridges.

## Layering conventions

- **Models** own data and invariants (`clean`, transitions, `display_title`).
- **Selectors** (`*/selectors.py`) are read-only and viewer-scoped.
- **Actions** (`*/actions.py`) handle POSTed daisIE actions and authorise.
- **Services** (`*/services.py`) coordinate multi-step writes and remote calls.
- **Signals** (`*/signals.py`) emit events and keep projections in sync —
  failure-isolated by design.

## Migrations and block serialization

Migrations are committed with each change. daisIE 3.5 serialises blocks by a
stable registry key, so page-body migrations are smaller; new blocks still
require `makemigrations` for every app whose StreamFields inherit the shared
block list (see [daisIE integration](daisie.md)).
