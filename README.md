# NEUROMANCERS Network

NEUROMANCERS offers a network for users to offer and request online support

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

License: MIT

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      uv run python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    uv run mypy neuromancers_network

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    uv run coverage run -m pytest
    uv run coverage html
    uv run open htmlcov/index.html

#### Running tests with pytest

    uv run pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html#using-webpack-or-gulp).

### Celery

This app comes with Celery.

To run a celery worker:

```bash
cd neuromancers_network
uv run celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important _where_ the celery commands are run. If you are in the same folder with _manage.py_, you should be right.

To run [periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html), you'll need to start the celery beat scheduler service. You can start it as a standalone process:

```bash
cd neuromancers_network
uv run celery -A config.celery_app beat
```

or you can embed the beat service inside a worker with the `-B` option (not recommended for production use):

```bash
cd neuromancers_network
uv run celery -A config.celery_app worker -B -l info
```

### Email Server

In development, it is often nice to be able to see emails that are being sent from your application. For that reason local SMTP server [Mailpit](https://github.com/axllent/mailpit) with a web interface is available as docker container.

Container mailpit will start automatically when you will run all docker containers.
Please check [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally-docker.html) for more details how to start all containers.

With Mailpit running, to view messages that are sent by your application, open your browser and go to `http://127.0.0.1:8025`

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).

---

## Quick Start (Local Development)

### Prerequisites

- Docker & Docker Compose
- [just](https://github.com/casey/just) command runner

### Setup

```bash
# 1. Generate the project (if starting fresh)
cookiecutter gh:cookiecutter/cookiecutter-django

# 2. Start all services
just up

# 3. Run migrations
just manage migrate

# 4. Create superuser
just manage createsuperuser

# 5. Load language fixtures
just manage loaddata languages_plus

# 6. Open the app
# http://localhost:8000
# Mailpit (email testing): http://localhost:8025
```

### Common Commands

| Command | Does |
|---------|------|
| `just up` | Start all Docker services |
| `just down` | Stop all services |
| `just test` | Run full test suite |
| `just manage <cmd>` | Run Django management command |
| `just shell` | Open Django shell_plus |
| `just logs <service>` | Tail logs for a service |

---

## Feature Overview

### User Accounts & Tiers
- Email-based authentication via **django-allauth** (social login: Google, Microsoft)
- Four account tiers: Seeker, Peer, Verified Peer, Admin
- Profiles with languages, tags, and profile pictures
- Tier progression managed by finite state machines (**django-fsm-2**)

### Sessions
- One-to-one and group session types
- Recurring sessions with full RRULE support (**django-recurrence**)
- Automatic Whereby video room creation
- Public and private visibility with object-level permissions (**django-guardian**)
- Admin-configurable boundary settings (auto-approval, concessionary pricing, etc.)
- Reviews and feedback (star rating + text)
- Host-attendee messaging via **django-notifications-hq**

### Payments
- Stripe integration via **dj-stripe** (webhooks auto-sync all objects)
- Three pricing types: fixed, hourly, concessionary
- Refund processing via Stripe dashboard or admin action
- Email notifications for all payment events (**django-anymail**)

### Calendar & Scheduling
- `.ics` file export for all sessions (**django-recurring**)
- Two-way Google Calendar and Microsoft Outlook sync
- iCloud CalDAV free/busy detection
- Proton Calendar manual import/export (no API available)
- Samsung Calendar syncs via Google/Microsoft account

### Administration
- Full Wagtail CMS with `ModelAdmin` for users, sessions, and tiers
- Site branding customisation: logo, fonts, colours (**wagtail-color-panel**)
- Editable admin guide page (**wagtail-markdown**)
- Customisable session filters

### Asset Storage
- All media and static assets stored on **GetPronto** (api.getpronto.io/v1)
- On-the-fly image transformations via URL parameters
- Global CDN delivery

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system diagram, data models, integration flows, and verified dependency register.

Key architectural decisions:
- **Monolithic Django + Wagtail** — no decoupled frontend; all interactivity via HTMX
- **Celery for async work** — calendar sync, email sending, asset processing
- **GetPronto REST API** — asset storage with CDN delivery (no Python SDK; direct HTTP integration)
- **PostgreSQL 18** — primary data store

---

## Environment Variables

Copy `.envs/.local/.django` and `.envs/.local/.postgres` from the template. Key variables:

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `STRIPE_SECRET_KEY` | Stripe secret API key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `DJSTRIPE_WEBHOOK_SECRET` | Same as above, for dj-stripe |
| `GETPRONTO_API_KEY` | GetPronto API key |
| `WHEREBY_API_KEY` | Whereby API key |
| `PROTON_SMTP_TOKEN` | Proton Mail SMTP token (generated in Proton Settings → IMAP/SMTP → SMTP tokens) |
| `PROTON_SMTP_EMAIL` | Proton Mail custom domain address used for sending (e.g. noreply@yourdomain.com) |
| `PROTON_SMTP_HOST` | Proton Mail SMTP host (default: `smtp.protonmail.ch`) |
| `PROTON_SMTP_PORT` | Proton Mail SMTP port (default: `587`) |
| `SENTRY_DSN` | Sentry project DSN |
| `REDIS_URL` | Redis connection URL (auto-set by Docker) |
| `DATABASE_URL` | PostgreSQL connection URL (auto-set by Docker) |

---

## Testing

```bash
# Run all tests
just test

# Run specific test file
just manage test sessions.tests.test_models

# Run with coverage
just coverage
```

Tests use **pytest-django** with **factory_boy** fixtures. A full test suite covers:
- User registration and authentication
- Session creation, booking, and visibility rules
- Stripe webhook handling
- Calendar sync task execution

---

## Deployment (Leapcell.io)

Deployment is automated via GitHub Actions:

1. Push to `main` triggers the CI/CD workflow
2. Workflow runs linting + tests with PostgreSQL
3. On success, Docker image is built and pushed to Leapcell
4. Leapcell CLI deploys the new image

### Manual Deployment

```bash
# Build and push Docker image
just deploy

# Or use Leapcell CLI directly
leapcell deploy
```

---

## Monitoring

- **Sentry**: Exception tracking and performance monitoring
- **Mailpit**: Local email testing (port 8025)
- **django-debug-toolbar**: Request/query profiling in development
- **Celery task results**: Viewable in Django admin (django-celery-results)

---

## Project Roadmap

See [ROADMAP.md](ROADMAP.md) for the complete 2-day implementation plan and task checklist.

**Day 1:** Core platform — authentication, user tiers, sessions, payments (Stripe), admin customisation, CI/CD pipeline.

**Day 2:** Advanced scheduling — `.ics` export, Google/Microsoft calendar sync, iCloud free/busy, reviews, messaging, end-to-end testing, client handover.

---

## Handover Criteria

- All features in the client brief are functional
- Automated tests pass on every push
- Code is consistently typed (`django-stubs` + `mypy`)
- Sentry error tracking active
- Production environment stable on Leapcell
- Admin users can modify site branding and content without touching code

---

## Dependencies

All primary dependencies have had releases in 2025 or 2026. See [ARCHITECTURE.md §3](ARCHITECTURE.md#3-verified-dependency-register-20252026-releases-only) for the full verified register with version pins and release dates.

```requirements
# Core
Django>=6.2
wagtail>=7.0
psycopg[binary]>=3.2

# Auth & Permissions
django-allauth>=65.13.0
django-guardian>=3.3.0

# Profiles
django-languages-plus>=2.1.1
django-taggit>=6.1.0
easy-thumbnails>=2.10.1

# State Machine
django-fsm-2>=4.2.4

# Frontend
django-htmx>=1.27.0
django-widget-tweaks>=1.5.1

# API
django-ninja>=1.5.0
django-cors-headers>=4.9.0
django-filter>=25.2

# Payments & Email
dj-stripe>=2.9.1
django-anymail>=14.0
stripe

# Async & Scheduling
celery>=5.5
django-celery-beat>=2.8.1
django-celery-results>=2.6.0
redis

# Calendar
django-recurrence>=1.14
django-recurring>=1.3.3
django5-scheduler>=1.0.1
google-api-python-client
msgraph-sdk
python-caldav>=2.0.1
icalendar>=6.3.2

# Notifications
django-notifications-hq>=1.8.3

# Security
django-cryptography>=2.0.3

# Admin
wagtail-color-panel>=1.7.1
wagtail-markdown>=0.13.0
django-colorfield>=0.14.0

# Asset Storage
httpx
django-storages>=1.14.6

# Monitoring
sentry-sdk

# Dev & Testing
django-extensions>=4.1
django-debug-toolbar>=6.1.0
factory_boy>=3.3.3
pytest-django>=4.11.1
django-stubs>=5.2.8
mypy
```