# NEUROMANCERS Network — Implementation Roadmap

**Delivery window:** 2 working days (parallel team + AI agents)  
**Target:** Feature‑complete production-ready platform for Leapcell.io deployment and client handover.

---

## Day 1: Core Platform (Authentication, Sessions, Payments, Admin)

| # | Task | Owner(s) | Dependencies | Done |
|---|------|----------|--------------|------|
| 1.1 | Generate project from `cookiecutter-django` (Docker, PostgreSQL, Celery, mailpit, …) with the recommended settings. Integrate Wagtail 7.x. | Infra lead | – | ☐ |
| 1.2 | Add core Python packages: `django-allauth`, `django-guardian`, `django-languages-plus`, `django-taggit`, `easy-thumbnails`, `django-fsm`, `django-htmx`, `django-ninja`, `dj-stripe`, `django.core.mail`. | Backend team | 1.1 | ☐ |
| 1.3 | Configure user model (`username_type = email`) and extend profile with: languages (m2m), tags (taggit), profile picture (easy-thumbnails). | Auth/profile dev | 1.2 | ☐ |
| 1.4 | Implement tier system (Seeker / Peer / Verified Peer / Admin) using Django groups and `django-guardian`. Add a state machine (`django-fsm`) to handle tier progression. | Auth dev | 1.3 | ☐ |
| 1.5 | Build Session model: type (1‑1 / group), date/time, recurrence (`django-recurrence`), Whereby room auto‑creation via REST API, optional user‑supplied link. | Sessions dev | 1.2 | ☐ |
| 1.6 | Add session visibility (public/private) with object‑level permissions (`django-guardian`). | Sessions dev | 1.5 | ☐ |
| 1.7 | Create session boundary settings (admin‑configurable JSON flags stored on Site settings). | Sessions dev | 1.5 | ☐ |
| 1.8 | Implement payment flow: Stripe Checkout for fixed/hourly/concessionary pricing using `dj-stripe`. Set up webhooks for payment confirmation, refund initiation, and automatic processing (later manual refund admin action for MVP). | Payments dev | 1.2, 1.5 | ☐ |
| 1.9 | Build notification backbone (`django-notifications-hq`) and configure Proton Mail SMTP backend (`django.core.mail`). Wire up payment confirmations, session booking alerts, and host‑attendee communication. | Comms dev | 1.2, 1.8 | ☐ |
| 1.10 | Create Wagtail admin sections: `ModelAdmin` for users/sessions/tiers, Site settings for branding (logo, colours via `wagtail-color-panel`), editable admin guide page (`wagtail-markdown`). | Admin dev | 1.1, 1.2 | ☐ |
| 1.11 | Build public‑facing templates (HTMX partials for interactivity) for session listing, filtering (`django-filter`), detail page, booking, profile management. | Frontend dev | 1.5, 1.3 | ☐ |
| 1.12 | Asset storage:  GetPronto: Generate SDK from [documentation](https://www.getpronto.io/docs/api-reference/overview). Use SDK for all asset operations, replacing cookiecutter default (AWS S3). | Infra/backend | 1.1 | ☐ |
| 1.13 | CI/CD pipeline: GitHub Actions workflow (test with PostgreSQL, lint, deploy to Leapcell via CLI). | Infra | 1.1 | ☐ |
| 1.14 | Basic test suite (factories + pytest) for critical paths: user registration, session creation, payment webhook. | QA / AI agents | 1.2–1.8 | ☐ |

## Day 2: Advanced Scheduling, Calendar Sync & Polish

| # | Task | Owner(s) | Dependencies | Done |
|---|------|----------|--------------|------|
| 2.1 | Implement `.ics` calendar export for sessions (`django-ical`). | Sessions dev | 1.5 | ☐ |
| 2.2 | Integrate Google Calendar sync: OAuth2 via `django-allauth`, store tokens, read free/busy, push session events using `google-api-python-client`. Celery beat task for periodic sync. | Calendar dev | 2.1, 2.3 | ☐ |
| 2.3 | Integrate Microsoft Graph sync: OAuth2, free/busy, push events (`msgraph-sdk`). Celery tasks. | Calendar dev | 2.1, 2.3 | ☐ |
| 2.4 | iCloud CalDAV integration (`python-caldav`): app‑specific password flow, read free/busy only, no remote push (user imports `.ics` manually). | Calendar dev | 2.1 | ☐ |
| 2.5 | Proton Calendar & Samsung Calendar: documentation + manual `.ics` import/export UI. | Calendar dev | 2.1 | ☐ |
| 2.6 | User calendar connection settings page (link/unlink providers). | Frontend dev | 2.2–2.5 | ☐ |
| 2.7 | Session reviews/feedback model (star rating + text) and display on profile. | Sessions dev | 1.5 | ☐ |
| 2.8 | Host‑attendee private messaging (basic in‑app messaging or extend notifications with reply capability). | Comms dev | 1.9 | ☐ |
| 2.9 | Finalise admin customisation (filters, tier modification, admin guide). | Admin dev | 1.10 | ☐ |
| 2.10 | End‑to‑end testing of full booking → payment → calendar sync flows. | QA / AI agents | All | ☐ |
| 2.11 | Performance profiling (Sentry APM, `django-debug-toolbar`), error handling hardening. | Infra | All | ☐ |
| 2.12 | Documentation: architecture overview, local setup guide, env variables reference, deployment guide. | Tech lead | All | ☐ |
| 2.13 | Client handover: demo, repository access, deployed instance on Leapcell. | Tech lead | All | ☐ |

---
## Handover Criteria
- All features listed in the client brief are functional.
- Automated tests pass on every push.
- Code is reviewed and consistently typed.
- Sentry error tracking active.
- Production environment stable on Leapcell.
- Admin users can modify site branding, content, and tier names without touching code.