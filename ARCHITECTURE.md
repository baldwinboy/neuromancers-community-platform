# NEUROMANCERS Network — Architecture Overview

**Stack:** Django 6.x + Wagtail 7.x · HTMX · Celery · PostgreSQL 18 · GetPronto  
**Deployment:** Leapcell.io via GitHub Actions  
**Last updated:** Day 0 — project generation

---

## 1. System Diagram

```
                              ┌─────────────────────┐
                              │   Web Browser        │
                              └──────────┬──────────┘
                                         │ HTTPS
                              ┌──────────▼──────────┐
                              │  Traefik (reverse    │
                              │  proxy, Let's Encrypt)│
                              └──┬───────────────┬──┘
                                 │               │
                    ┌────────────▼──┐      ┌─────▼──────────┐
                    │ Django/Wagtail │      │  PostgreSQL 18  │
                    │  (Gunicorn)    │◄────►│                 │
                    └───────┬────────┘      └────────────────┘
                            │
                            │ Redis (Celery broker + cache)
                            ▼
                    ┌───────────────┐
                    │ Celery Worker │────── External APIs
                    └───────────────┘
```

External APIs: Stripe (payments), Whereby (video rooms), GetPronto (asset storage), Google Calendar, Microsoft Graph, iCloud CalDAV.

---

## 2. Core Technology Stack

| Layer | Component | Version / Pin |
|-------|-----------|---------------|
| **Framework** | Django + Wagtail | Django 6.x, Wagtail 7.x |
| **Auth** | django-allauth | ≥65.13.0 |
| **Permissions** | django-guardian | ≥3.3.0 |
| **API** | Django Ninja | ≥1.5.0 |
| **Frontend** | HTMX + Django templates | django-htmx ≥1.27.0 |
| **Task Queue** | Celery + Redis | Celery 5.5+, django-celery-beat ≥2.8.1, django-celery-results ≥2.6.0 |
| **Database** | PostgreSQL 18 | psycopg (binary) |
| **Asset Storage** | GetPronto | REST API (api.getpronto.io/v1) |
| **Caching** | Redis | Also Celery broker |
| **Email** | Proton Mail SMTP | Direct SMTP submission, django.core.mail |
| **Payments** | Stripe via dj-stripe | dj-stripe ≥2.9.1 |
| **Video Rooms** | Whereby REST API | `requests` / `httpx` |
| **Calendar Sync** | Google API, Microsoft Graph, CalDAV (python-caldav) | Async via Celery |
| **Monitoring** | Sentry | sentry-sdk ≥2.x |
| **CI/CD** | GitHub Actions → Leapcell.io | Docker Compose |

---

## 3. Verified Dependency Register (2025/2026 Releases Only)

Only packages with at least one release in 2025 or 2026 are included below. Each entry lists the latest version and release window confirmed via PyPI / Django Packages.

### Core Django Packages

| Package | Latest | Released | Role |
|----------|--------|----------|------|
| django-allauth | 65.13.0 | Oct 2025 | Authentication, social login, MFA |
| django-guardian | 3.3.0 | Feb 2026 | Object-level permissions |
| django-taggit | 6.1.0 | 2025 | Tagging for profiles & sessions |
| easy-thumbnails | 2.10.1 | Aug 2025 | Profile picture resizing |
| django-fsm-2 | 4.2.4 | Mar 2026 | Finite state machine (tier progression, session status) |
| django-htmx | 1.27.0 | Nov 2025 | HTMX integration helpers |
| django-ninja | 1.5.0 | Nov 2025 | Type-safe REST API framework |
| django-filter | 25.2 | Oct 2025 | Session listing filters |
| django-recurrence | 1.14 | Dec 2025 | Recurring date rules (RRULE) |
| django-recurring | 1.3.3 | Mar 2026 | iCal-compatible calendar entries, .ics export |
| django5-scheduler | 1.0.1 | May 2025 | Calendar UI & event management |
| django-notifications-hq | 1.8.3 | 2025 | In-app notification system |
| django-widget-tweaks | 1.5.1 | Jan 2026 | Form field CSS class manipulation |
| django-extensions | 4.1 | 2025 | Dev helpers (shell_plus, graph_models) |
| django-debug-toolbar | 6.1.0 | 2025 | Request/query profiling |
| django-cors-headers | 4.9.0 | Sep 2025 | CORS headers |
| django-colorfield | 0.14.0 | Apr 2025 | Colour picker field for models |
| django-storages | 1.14.6 | Apr 2025 | Storage backend abstraction (not used for primary storage in this project) |

### Wagtail CMS Packages

| Package | Latest | Released | Role |
|----------|--------|----------|------|
| Wagtail | 6.3 LTS | – | CMS, ModelAdmin, Site settings |
| wagtail-color-panel | 1.7.1 | Nov 2025 | Colour picker for Wagtail admin |
| wagtail-markdown | 0.13.0 | Oct 2025 | Markdown fields & StreamField blocks |

### Payments & Email

| Package | Latest | Released | Role |
|----------|--------|----------|------|
| dj-stripe | 2.9.1 | Apr 2025 | Stripe object sync, webhook handling |
| django.core.mail | – | Built-in | SMTP backend for Proton Mail submission |

### Async & Scheduling

| Package | Latest | Released | Role |
|----------|--------|----------|------|
| Celery | 5.5+ | 2025 | Distributed task queue |
| django-celery-beat | 2.8.1 | May 2025 | DB-backed periodic task scheduler |
| django-celery-results | 2.6.0 | Apr 2025 | DB-backed task result storage |

### Security

| Package | Latest | Released | Role |
|----------|--------|----------|------|
| django-cryptography | 2.0.3 | Jan 2025 | Model field encryption (calendar credentials) |

### Calendar Sync Providers

| Package | Latest | Released | Role |
|----------|--------|----------|------|
| google-api-python-client | 2.x | Active | Google Calendar API |
| msgraph-sdk | 1.x | Active | Microsoft Graph API |
| python-caldav | 2.0.1 | 2025 | iCloud CalDAV client |
| icalendar | 6.3.2 | 2025 | .ics file parse/generate |

### Development & Testing

| Package | Latest | Released | Role |
|----------|--------|----------|------|
| factory_boy | 3.3.3 | 2025 | Test fixture factories |
| pytest-django | 4.11.1 | 2025 | Pytest plugin for Django |
| django-stubs | 5.2.8 | Dec 2025 | Type stubs for mypy |
| sentry-sdk | 2.x | 2025 | Error & performance monitoring |

### Packages with Acceptable Stability (Pre-2025 Latest, but Actively Maintained)

*   **django-languages-plus (2.1.1)** — Last PyPI release January 2024. However, it is a simple model + fixture package that has been tested against Django 5.x. Its static data (language codes) does not require frequent updates. The project repository shows activity within 3 months, and Socket.dev reports a "healthy version release cadence." Included as a stable dependency.

### Packages Replaced (Pre-2025 Last Release, No Active Maintenance Signal)

*   **django-fsm → django-fsm-2**: Original django-fsm last released 2.8.1 in 2022. django-fsm-2 (v4.2.4, March 2026) is a maintained fork with identical API, full Django 5.x support, and active releases.
*   **django-ical → django-recurring**: django-ical last released 1.9.2 in June 2023. django-recurring (v1.3.3, March 2026) provides both recurrence handling and iCal-compatible .ics export in a single package, eliminating the need for a separate iCal library.
*   **django-encrypted-model-fields → django-cryptography**: django-encrypted-model-fields last released 0.6.5 in February 2022. django-cryptography (v2.0.3, January 2025) wraps the Python Cryptography library, supports Django 5.x, and is actively maintained.

---

## 4. Key Data Models (Simplified)

*   **User** — Extends `AbstractUser`, `username_type=email`. Linked 1:1 to `Profile`.
*   **Profile** — Display name, bio, languages (M2M to `django-languages-plus`), tags (`django-taggit`), avatar (`easy-thumbnails`), tier state (`django-fsm-2`).
*   **Tier** — Managed via Django groups + `Profile.tier` state machine. Tiers: `seeker`, `peer`, `verified_peer`, `admin`.
*   **Session** — Title, description, type (`1-on-1` / `group`), host (FK to User), start/end, recurrence (`django-recurrence`), visibility (`public` / `private`), boundary flags (JSON), price (FK to Stripe `Price` via `dj-stripe`), attendees (M2M via `Attendance`), Whereby room URL, user-supplied link fallback.
*   **Payment** — dj-stripe models: `Customer`, `PaymentIntent`, `Refund`.
*   **Review** — Session-bound star rating + comment.
*   **Notification** — Via `django-notifications-hq`.
*   **CalendarConnection** — Encrypted credentials (`django-cryptography`), provider type (`google`, `microsoft`, `caldav`), FK to User.

---

## 5. Integration Flows

### 5.1 GetPronto Asset Storage

1.  User uploads a file via Django form.
2.  View saves the file temporarily, then calls a utility function that POSTs to `https://api.getpronto.io/v1/files` with the API key header `Authorization: ApiKey YOUR_API_KEY`.
3.  On success, the returned file URL is stored on the model.
4.  On-the-fly image transformations are applied via URL query parameters (e.g., `?width=200&height=200&fit=cover`) per [GetPronto documentation](https://www.getpronto.io/docs/api-reference/overview).
5.  A Celery task handles the upload for large files to avoid blocking the HTTP request.

### 5.2 Stripe Payment Webhook

1.  User initiates Stripe Checkout → Stripe sends `checkout.session.completed`.
2.  `dj-stripe` webhook handler syncs objects to local DB.
3.  Celery task sends email confirmation and updates attendance status.

### 5.3 Whereby Room Creation

1.  On `Session.save()` (if no room URL and host has tier permission), call Whereby REST API to create a meeting room.
2.  Store returned URL; fallback to user-supplied link on API failure.

### 5.4 Calendar Sync (Day 2)

*   **Google & Microsoft**: OAuth2 via `django-allauth`. Celery beat task every 15 min reads free/busy. On session publish/update, a Celery task pushes the event.
*   **iCloud (CalDAV)**: App-specific password stored encrypted via `django-cryptography`. Read free/busy only; no remote push. Users download `.ics` file.
*   **Proton / Samsung**: Proton has no API — manual `.ics` import/export only. Samsung syncs through Google/Microsoft accounts; no separate code required.

### 5.5 Email Delivery

1. Django sends email via `django.core.mail.backends.smtp.EmailBackend`.
2. SMTP connection to `smtp.protonmail.ch:587` with STARTTLS.
3. Authentication uses SMTP token generated in Proton Mail settings.

---

## 6. Authentication & Security

*   Email-only login (no username). Social login (Google/Microsoft) mapped to email by `django-allauth`, preventing duplicate accounts.
*   Django session-based auth with CSRF protection.
*   Calendar credentials encrypted at rest using `django-cryptography` (Fernet symmetric encryption).
*   Stripe webhooks verified with signing secret.
*   All transactional emails sent via TLS through Mailgun.

---

## 7. Deployment (Leapcell.io)

1.  GitHub Actions workflow runs tests with PostgreSQL service on every push.
2.  On push to `main`, workflow builds Docker image, pushes to registry, and deploys via Leapcell CLI.
3.  Production env vars stored in Leapcell's secrets manager.
4.  Traefik (shipped with cookiecutter-django) handles SSL termination.

---

## 8. Developer Workflow

*   `just up` — Start all services (web, db, redis, celery, mailpit).
*   `just test` — Run pytest suite.
*   `just manage …` — Run Django management commands.
*   Mailpit catches all outgoing emails on port 8025.
*   Pre-commit hooks (black, isort, ruff) enforce code style.
*   All new code accompanied by `factory_boy` factories and `pytest` tests.

---

## 9. Open Items & Future Considerations

*   **GetPronto Python SDK**: No official Python SDK exists at time of writing. The integration uses direct REST API calls via `httpx`. If GetPronto releases a Python SDK, the utility module can be swapped without model changes.
*   **Recurring Sessions**: Full RRULE support via `django-recurrence`. Initial calendar push handles single instances only; recurring series push is a post-handover enhancement.
*   **iCloud Write-back**: Not implemented; users must import `.ics` files manually.
*   **Proton Calendar**: No API exists; fully manual workflow.
```
